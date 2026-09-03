"""대국민서비스 '나의 사건검색' 클라이언트 (CAPTCHA 반자동).

  https://ssgo.scourt.go.kr/   (구 safind 가 ssgo 로 이전됨)

사건검색에는 자동입력 방지문자(CAPTCHA)가 있어 완전 자동화가 불가능하다.
따라서 2단계로 나눈다.

  1) start_challenge(): 폼을 채운 뒤 CAPTCHA 이미지를 파일로 저장하고
     세션(브라우저 컨텍스트)을 살려둔 채 사용자에게 이미지를 보여준다.
  2) submit_answer(): 사용자가 읽은 CAPTCHA 값을 입력해 조회를 완료한다.

세션은 메모리 딕셔너리에 보관하며 TTL(기본 3분)이 지나면 정리한다.

셀렉터는 WebSquare 내부 id 의 suffix 로 매칭한다(라이브 DOM 검증 완료, 2026-06).
실제 id 예: mf_ssgoTopMainTab_contents_content1_body_sbx_cortCd
"""

from __future__ import annotations

import asyncio
import os
import re
import time
import uuid
from dataclasses import dataclass, field

from playwright.async_api import BrowserContext, Page

from .browser import manager
from .models import CaptchaChallenge, CaseInfo

SEARCH_URL = "https://ssgo.scourt.go.kr/"

# CAPTCHA 이미지를 저장할 디렉토리.
# 기본값을 os.getcwd() 로 두면 MCP 서버의 작업 디렉터리(앱이 띄우면 보통
# C:\Windows\System32)에 쓰려다 PermissionError(EACCES)가 난다.
# 저장소 루트의 .captcha 폴더를 기본값으로 사용한다(항상 쓰기 가능).
# Cowork 등에서 Claude 가 이미지를 직접 읽어야 하면 LAWYER_MCP_CAPTCHA_DIR 로
# 연결된(읽기 가능한) 폴더를 지정하면 된다.
_REPO_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
_CAPTCHA_DIR = os.environ.get("LAWYER_MCP_CAPTCHA_DIR") or os.path.join(
    _REPO_ROOT, ".captcha"
)
os.makedirs(_CAPTCHA_DIR, exist_ok=True)
# 세션 유효시간. CAPTCHA 이미지를 사람(또는 에이전트)이 읽고 되돌려주기까지
# MCP 왕복이 끼기 때문에 넉넉히 잡는다. TTL 이 지난 세션은 다음 호출 때 정리된다.
_SESSION_TTL = float(os.environ.get("LAWYER_MCP_SESSION_TTL", "600"))

# 세션에 물려 있지 않은 CAPTCHA 이미지를 지우기까지의 유예. 프로세스가 비정상
# 종료되면 _sessions 는 사라져도 파일은 디스크에 남으므로 별도로 걷어낸다.
_CAPTCHA_MAX_AGE = 3600.0  # 초

# --- 라이브 검증 완료 셀렉터 (suffix 매칭) -------------------------------
_SEL_COURT = "select[id$='_sbx_cortCd']"        # 법원 선택
_SEL_YEAR = "select[id$='_sbx_csYr']"           # 년도
_SEL_DIVISION = "select[id$='_sbx_csDvsCd']"    # 사건구분 (가/나/타경/자 ...)
_SEL_SERIAL = "input[id$='_ibx_csSerial']"      # 사건일련번호
_SEL_FULLNO = "input[id$='_ibx_fullCsNo']"      # 사건번호 일괄입력(대체 모드)
_SEL_PARTY = "input[id$='_ibx_btprNm']"         # 당사자명 (필수)
_SEL_CAPTCHA_IMG = "img[id$='_img_captcha']"
_SEL_CAPTCHA_INPUT = "input[id$='_ibx_answer']"
_SEL_SUBMIT = "input[id$='_btn_srchCs']"        # 검색 버튼
# -------------------------------------------------------------------------

# 사건번호 형식: "25자10000", "2025자10000", "2024가단12345"
_CASE_RE = re.compile(r"(?P<year>\d{2,4})\s*(?P<div>[가-힣]+)\s*(?P<serial>\d+)")


def parse_case_no(case_no: str) -> tuple[str, str, str]:
  """'25자10000' -> ('2025', '자', '10000'). 2자리 연도는 4자리로 보정."""
  m = _CASE_RE.search(case_no.strip())
  if not m:
    raise ValueError(
      f"사건번호 형식을 인식할 수 없습니다: {case_no!r} (예: '25자10000')"
    )
  year = m.group("year")
  if len(year) == 2:
    yy = int(year)
    # 50 미만은 2000년대, 이상은 1900년대로 본다(법원 전산 범위 기준 충분).
    year = str(2000 + yy if yy < 50 else 1900 + yy)
  return year, m.group("div"), m.group("serial")


@dataclass
class _Session:
  context: BrowserContext
  page: Page
  created_at: float = field(default_factory=lambda: time.monotonic())
  court: str = ""
  case_no: str = ""
  captcha_path: str = ""


# session_id -> _Session
_sessions: dict[str, _Session] = {}


def _remove_quietly(path: str) -> None:
  """파일을 조용히 지운다(이미 없거나 잠겨 있어도 무시)."""
  if not path:
    return
  try:
    os.remove(path)
  except OSError:
    pass


async def _close_session(sess: _Session) -> None:
  """세션의 브라우저 컨텍스트와 CAPTCHA 이미지를 함께 정리한다."""
  try:
    await sess.context.close()
  except Exception:
    pass
  _remove_quietly(sess.captcha_path)


async def _gc_sessions() -> None:
  """TTL 지난 세션과 그 CAPTCHA 이미지를 정리한다.

  조회를 시작하는 쪽(start_challenge)과 끝내는 쪽(submit_answer) 양쪽에서
  호출한다. 한쪽에서만 돌리면 사용자가 CAPTCHA 를 풀지 않고 중단했을 때
  버려진 컨텍스트가 다음 조회 때까지 살아남는다.
  """
  now = time.monotonic()
  expired = [sid for sid, s in _sessions.items() if now - s.created_at > _SESSION_TTL]
  for sid in expired:
    await _close_session(_sessions.pop(sid))


def _sweep_captcha_dir() -> None:
  """세션에 물려 있지 않은 오래된 CAPTCHA 이미지를 삭제한다.

  우리가 만든 `captcha_*.png` 만 대상으로 한다. LAWYER_MCP_CAPTCHA_DIR 로
  사용자가 다른 용도의 폴더를 지정했을 수 있기 때문이다.
  """
  live = {s.captcha_path for s in _sessions.values()}
  cutoff = time.time() - _CAPTCHA_MAX_AGE
  try:
    names = os.listdir(_CAPTCHA_DIR)
  except OSError:
    return
  for name in names:
    if not (name.startswith("captcha_") and name.endswith(".png")):
      continue
    path = os.path.join(_CAPTCHA_DIR, name)
    if path in live:
      continue
    try:
      if os.path.getmtime(path) < cutoff:
        os.remove(path)
    except OSError:
      pass


async def _select_by_value_or_label(page: Page, selector: str, value: str) -> None:
  """value 우선, 실패하면 label 로 select 옵션을 고른다."""
  try:
    await page.select_option(selector, value=value)
    return
  except Exception:
    pass
  await page.select_option(selector, label=value)


async def start_challenge(
  court: str,
  case_no: str,
  party_name: str,
  case_type: str | None = None,
) -> CaptchaChallenge:
  """1단계: 폼을 채우고 CAPTCHA 이미지를 저장한 뒤 세션을 보존한다.

  Args:
    court: 법원명 (예: '여수시법원'). select 옵션과 정확히 일치해야 함.
    case_no: 사건번호 (예: '25자10000').
    party_name: 당사자명. ssgo 사건검색은 당사자명이 필수입력이다.
    case_type: 미사용(사건구분은 case_no 에서 자동 파싱). 호환용 파라미터.
  """
  await _gc_sessions()
  _sweep_captcha_dir()
  year, division, serial = parse_case_no(case_no)

  context, page = await manager.new_persistent_page()
  # networkidle 은 WebSquare 정부 사이트의 지속적 네트워크 활동 때문에 도달하지
  # 못해 타임아웃의 원인이 된다. domcontentloaded 로 빠르게 받고, 아래의
  # 폼 셀렉터 대기(_SEL_SERIAL)로 렌더링 완료를 보장한다.
  await page.goto(SEARCH_URL, wait_until="domcontentloaded", timeout=30000)

  # WebSquare 폼이 그려질 때까지 핵심 입력칸을 기다린다.
  await page.wait_for_selector(_SEL_SERIAL, timeout=20000)

  await _select_by_value_or_label(page, _SEL_COURT, court)
  await _select_by_value_or_label(page, _SEL_YEAR, year)
  await _select_by_value_or_label(page, _SEL_DIVISION, division)
  await page.fill(_SEL_SERIAL, serial)
  await page.fill(_SEL_PARTY, party_name)

  # CAPTCHA 이미지 캡처 (src 가 blob: 이라 요소 스크린샷으로 받는다)
  session_id = uuid.uuid4().hex[:12]
  img_path = os.path.join(_CAPTCHA_DIR, f"captcha_{session_id}.png")
  await page.wait_for_selector(_SEL_CAPTCHA_IMG, timeout=10000)
  # blob: 이미지는 요소가 DOM 에 붙어도 픽셀 디코드 전이면 빈/라벨 영역이 찍힌다.
  # naturalWidth 가 잡힐 때까지(=이미지 로드 완료) 기다려 실제 문자 이미지를
  # 보장한다. 못 기다려도(타임아웃) 일단 캡처는 진행한다.
  cap = page.locator(_SEL_CAPTCHA_IMG).first
  try:
    await cap.evaluate(
      "el => (el.complete && el.naturalWidth > 0) ? true : new Promise(res => {"
      " el.addEventListener('load', () => res(true), { once: true });"
      " setTimeout(() => res(true), 5000); })"
    )
  except Exception:
    pass
  await cap.screenshot(path=img_path)

  _sessions[session_id] = _Session(
    context=context, page=page, court=court, case_no=case_no, captcha_path=img_path
  )

  return CaptchaChallenge(
    session_id=session_id,
    captcha_image_path=img_path,
    message=(
      "저장된 CAPTCHA 이미지를 열어 표시된 문자를 읽고, "
      "case_search_submit 툴에 session_id 와 함께 입력하세요. "
      f"(세션 유효시간 {int(_SESSION_TTL)}초)"
    ),
  )


def _cell(t: str | None) -> str | None:
  if t is None:
    return None
  s = t.strip()
  return s or None


# 결과 상세 그리드의 안정적 id suffix (라이브 검증 완료, 2026-06)
_GRID_SUFFIX = {
  "hearings": "_grd_rcntDxdyLst_body_table",       # 기일내역
  "submissions": "_grd_rcntSbmsnDocmtLst_body_table",  # 제출서류 접수내역
  "parties": "_grd_btprtCttLst_body_table",        # 당사자내역
  "agents": "_grd_agntCttLst_body_table",          # 대리인내역
}


async def _extract_result(page) -> dict:
  """상세 화면에서 기본정보(라벨/값 쌍)와 4개 그리드를 구조화해 추출한다."""
  return await page.evaluate(
    """(gridSuffix) => {
      const txt = (el) => (el.innerText || '').trim();

      // 1) 기본정보: '사건번호'와 '사건명'을 모두 포함한 테이블을 찾아 라벨/값 쌍 파싱
      const basic = {};
      for (const tb of document.querySelectorAll('table')) {
        const t = txt(tb);
        if (t.includes('사건번호') && t.includes('사건명')) {
          for (const tr of tb.querySelectorAll('tr')) {
            const cells = [...tr.querySelectorAll('th,td')].map(txt);
            for (let i = 0; i + 1 < cells.length; i += 2) {
              const k = cells[i], v = cells[i + 1];
              if (k) basic[k] = v;
            }
          }
          break;
        }
      }

      // 2) 그리드: 첫 행을 헤더로 보고 나머지를 dict 로 변환
      const grid = (suffix) => {
        const tb = [...document.querySelectorAll('table')]
          .find(t => t.id && t.id.endsWith(suffix));
        if (!tb) return [];
        const rows = [...tb.querySelectorAll('tr')]
          .map(tr => [...tr.querySelectorAll('th,td')].map(txt))
          .filter(r => r.some(x => x));
        if (rows.length < 2) return [];
        const header = rows[0];
        return rows.slice(1).map(r => {
          const o = {};
          header.forEach((h, i) => { o[h || ('col' + i)] = r[i] ?? ''; });
          return o;
        });
      };

      const out = { basic };
      for (const [key, suffix] of Object.entries(gridSuffix)) {
        out[key] = grid(suffix);
      }
      return out;
    }""",
    _GRID_SUFFIX,
  )


def _dialog_error(messages: list[str]) -> ValueError:
  """법원 사이트 경고창 문구를 그대로 실패 사유로 옮긴다."""
  msg = " / ".join(m.strip() for m in messages if m and m.strip())
  return ValueError(
    "조회 실패: "
    + (msg or "법원 사이트가 경고창을 표시했습니다.")
    + " (사건번호·당사자명·자동입력 방지문자를 확인하세요)"
  )


async def _result_rendered(page: Page) -> bool:
  """상세 화면(기본정보 테이블)이 그려졌는지 확인한다."""
  try:
    return await page.evaluate(
      "() => document.body.innerText.includes('사건번호')"
      " && document.body.innerText.includes('재판부')"
    )
  except Exception:
    return False


async def submit_answer(session_id: str, captcha_text: str) -> CaseInfo:
  """2단계: CAPTCHA 값을 입력해 조회를 완료하고 결과를 파싱한다."""
  await _gc_sessions()
  sess = _sessions.get(session_id)
  if sess is None:
    raise ValueError(
      "세션을 찾을 수 없습니다(만료되었거나 잘못된 session_id). "
      "case_search_captcha 부터 다시 시작하세요."
    )

  page = sess.page

  # 조회 실패 시 법원 사이트는 JS alert() 로 안내한다(당사자명 불일치,
  # 자동입력 방지문자 오류, 조회결과 없음 등). 핸들러가 없으면 자동으로
  # 닫혀 사라지므로, 메시지를 가로채 그대로 에러로 surface 한다.
  dialog_messages: list[str] = []

  async def _on_dialog(dialog):
    dialog_messages.append(dialog.message)
    try:
      await dialog.accept()
    except Exception:
      pass

  page.on("dialog", _on_dialog)
  try:
    await page.fill(_SEL_CAPTCHA_INPUT, captcha_text)
    await page.click(_SEL_SUBMIT)

    # 결과 렌더링과 경고창 중 **먼저 도착하는 쪽**을 기다린다.
    # networkidle 은 WebSquare 정부 사이트에서 도달하지 못해 불필요한 30초
    # 지연만 유발하고, 반대로 짧은 고정 sleep 으로 경고창을 판정하면 느린
    # 네트워크에서 늦게 뜬 경고창을 놓쳐 실제 실패 사유(당사자명 불일치,
    # CAPTCHA 오류)가 아래의 일반 메시지로 뭉개진다.
    deadline = time.monotonic() + 15.0
    while time.monotonic() < deadline:
      if dialog_messages or await _result_rendered(page):
        break
      await asyncio.sleep(0.25)

    # 1) 경고창이 떴다면 그 문구가 곧 실패 사유다.
    if dialog_messages:
      raise _dialog_error(dialog_messages)

    raw = await _extract_result(page)

    # 2) 경고창 없이 검색 폼/결과목록으로 되돌아온 경우(상세 진입 실패) 감지.
    #    상세 페이지라면 기본정보에 '사건명' 또는 '재판부'가 반드시 존재한다.
    b = raw["basic"]
    if not (b.get("사건명") or b.get("재판부")):
      # 판정 직전에 뜬 경고창이 있을 수 있으니 마지막으로 한 번 더 살핀다.
      if not dialog_messages:
        await asyncio.sleep(1.0)
      if dialog_messages:
        raise _dialog_error(dialog_messages)
      raise ValueError(
        "조회 결과를 찾을 수 없습니다. 사건번호와 당사자명이 정확한지 "
        "확인하세요. (당사자명이 일치하지 않거나 해당 사건이 없을 수 있습니다.)"
      )

    info = CaseInfo(court=sess.court, case_no=sess.case_no)
    info.basic_info = b
    info.case_name = b.get("사건명")
    info.department = b.get("재판부")
    info.filed_date = b.get("접수일")
    info.final_result = b.get("종국결과") or None
    # 원고/피고 또는 신청인/피신청인 요약
    pl = b.get("원고") or b.get("신청인") or b.get("채권자")
    de = b.get("피고") or b.get("피신청인") or b.get("채무자")
    if pl or de:
      info.parties_summary = " / ".join(
        x for x in (f"원고 {pl}" if pl else None, f"피고 {de}" if de else None) if x
      )
    info.hearings = raw["hearings"]
    info.submissions = raw["submissions"]
    info.parties = raw["parties"]
    info.agents = raw["agents"]
    return info
  finally:
    # 성공/실패와 무관하게 컨텍스트와 CAPTCHA 이미지를 함께 정리한다.
    # 이미지를 남겨두면 조회할 때마다 .captcha 폴더에 계속 쌓인다.
    _sessions.pop(session_id, None)
    await _close_session(sess)
