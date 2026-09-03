"""CAPTCHA 이미지·세션 정리 로직 단위 테스트.

브라우저 없이 돌아야 하므로 컨텍스트는 대역(_FakeContext)으로 바꾸고,
CAPTCHA 폴더는 임시 디렉터리로 갈아끼운다.
"""

import asyncio
import os
import time

import pytest

from lawyer_mcp import scourt


class _FakeContext:
  """close() 호출 여부만 기록하는 BrowserContext 대역."""

  def __init__(self) -> None:
    self.closed = False

  async def close(self) -> None:
    self.closed = True


@pytest.fixture
def captcha_dir(tmp_path, monkeypatch):
  """실제 .captcha 폴더와 전역 세션 딕셔너리를 건드리지 않도록 격리한다."""
  monkeypatch.setattr(scourt, "_CAPTCHA_DIR", str(tmp_path))
  monkeypatch.setattr(scourt, "_sessions", {})
  return tmp_path


def _write(dir_path, name: str, age_sec: float = 0.0) -> str:
  """지정한 나이(수정시각)로 파일을 만든다."""
  path = dir_path / name
  path.write_bytes(b"png")
  stamp = time.time() - age_sec
  os.utime(path, (stamp, stamp))
  return str(path)


class TestSweepCaptchaDir:
  def test_removes_old_orphan(self, captcha_dir):
    old = _write(captcha_dir, "captcha_aaa.png", scourt._CAPTCHA_MAX_AGE + 60)
    scourt._sweep_captcha_dir()
    assert not os.path.exists(old)

  def test_keeps_recent_file(self, captcha_dir):
    fresh = _write(captcha_dir, "captcha_bbb.png", 10)
    scourt._sweep_captcha_dir()
    assert os.path.exists(fresh)

  def test_keeps_file_held_by_live_session(self, captcha_dir):
    """세션이 살아 있으면 오래됐어도 지우지 않는다."""
    held = _write(captcha_dir, "captcha_ccc.png", scourt._CAPTCHA_MAX_AGE + 60)
    scourt._sessions["live"] = scourt._Session(
      context=_FakeContext(), page=None, captcha_path=held
    )
    scourt._sweep_captcha_dir()
    assert os.path.exists(held)

  def test_ignores_foreign_files(self, captcha_dir):
    """LAWYER_MCP_CAPTCHA_DIR 에 다른 파일이 있어도 건드리지 않는다."""
    other = _write(captcha_dir, "notes.txt", scourt._CAPTCHA_MAX_AGE + 60)
    png = _write(captcha_dir, "screenshot.png", scourt._CAPTCHA_MAX_AGE + 60)
    scourt._sweep_captcha_dir()
    assert os.path.exists(other)
    assert os.path.exists(png)

  def test_survives_missing_directory(self, captcha_dir, monkeypatch):
    """폴더가 없어도 예외를 던지지 않는다."""
    monkeypatch.setattr(scourt, "_CAPTCHA_DIR", str(captcha_dir / "nope"))
    scourt._sweep_captcha_dir()  # 예외가 나지 않으면 통과


class TestGcSessions:
  def test_expired_session_is_closed_and_image_removed(self, captcha_dir):
    img = _write(captcha_dir, "captcha_ddd.png")
    ctx = _FakeContext()
    scourt._sessions["old"] = scourt._Session(
      context=ctx,
      page=None,
      created_at=time.monotonic() - scourt._SESSION_TTL - 1,
      captcha_path=img,
    )

    asyncio.run(scourt._gc_sessions())

    assert "old" not in scourt._sessions
    assert ctx.closed
    assert not os.path.exists(img)

  def test_live_session_is_untouched(self, captcha_dir):
    img = _write(captcha_dir, "captcha_eee.png")
    ctx = _FakeContext()
    scourt._sessions["live"] = scourt._Session(
      context=ctx, page=None, captcha_path=img
    )

    asyncio.run(scourt._gc_sessions())

    assert "live" in scourt._sessions
    assert not ctx.closed
    assert os.path.exists(img)


class TestDialogError:
  def test_carries_site_message(self):
    """법원 사이트 경고창 문구가 그대로 전달돼야 한다."""
    err = scourt._dialog_error(["자동입력 방지문자가 일치하지 않습니다."])
    assert "자동입력 방지문자가 일치하지 않습니다." in str(err)

  def test_joins_multiple_messages(self):
    err = scourt._dialog_error(["첫 번째", "두 번째"])
    assert "첫 번째" in str(err) and "두 번째" in str(err)

  def test_falls_back_when_all_blank(self):
    err = scourt._dialog_error(["", "   "])
    assert "경고창" in str(err)
