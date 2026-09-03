"""검증/탐침 스크립트 공용 설정 — 출력 인코딩과 산출물 경로.

**이 모듈을 임포트하면 stdout/stderr 가 UTF-8 로 재설정된다.** Windows 기본
콘솔 인코딩(cp949)에서는 한글 출력이 깨지고, 파일로 리다이렉트하면 cp949 로
기록돼 나중에 읽을 때 또 깨진다. 그래서 `PYTHONIOENCODING=utf-8` 을 매번
지정하지 않아도 되도록 런타임에 직접 맞춘다.

산출물(스크린샷·DOM 덤프·CAPTCHA 답안)은 개발자마다 다른 절대경로 대신
**저장소 루트**에 저장한다. 다른 위치를 쓰려면 `LAWYER_MCP_OUT_DIR` 를 지정한다.

  $env:LAWYER_MCP_OUT_DIR = "D:\\tmp\\lawyer"   # PowerShell
"""

import os
import sys

# --- 출력 인코딩 ----------------------------------------------------------
# 이미 열려 있는 스트림이라 PYTHONIOENCODING 은 이 프로세스에 소급 적용되지
# 않는다. reconfigure 로 직접 바꾸고, 환경변수는 자식 프로세스용으로 남긴다.
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
for _stream in (sys.stdout, sys.stderr):
  try:
    _stream.reconfigure(encoding="utf-8")
  except (AttributeError, ValueError):
    # TextIOWrapper 가 아니거나(파이프 래핑 등) 이미 분리된 스트림은 건너뛴다.
    pass

# --- 산출물 경로 ----------------------------------------------------------
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

OUT_DIR = os.environ.get("LAWYER_MCP_OUT_DIR") or _REPO_ROOT


def out(name: str) -> str:
  """산출물 파일 이름을 OUT_DIR 기준 절대경로로 바꾼다."""
  os.makedirs(OUT_DIR, exist_ok=True)
  return os.path.join(OUT_DIR, name)
