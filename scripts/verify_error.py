"""조회 실패 에러 처리 검증 — 일부러 틀린 당사자명으로 조회한다.

  uv run python scripts/verify_error.py
submit_answer 가 명확한 ValueError 를 던지면 성공.
"""

import asyncio
import os

from lawyer_mcp import scourt
from lawyer_mcp.browser import manager
from _common import out

# 실제 사건 정보는 저장소에 두지 않는다. 환경변수로 주입해 사용한다.
COURT = os.environ.get("LAWYER_MCP_TEST_COURT", "○○시법원")
CASE_NO = os.environ.get("LAWYER_MCP_TEST_CASE_NO", "25자10000")
PARTY = "존재하지않는당사자"  # 일부러 틀린 이름
ANSWER_FILE = out("captcha_answer.txt")


async def main():
  if os.path.exists(ANSWER_FILE):
    os.remove(ANSWER_FILE)

  ch = await scourt.start_challenge(COURT, CASE_NO, PARTY)
  print("[1] CAPTCHA 저장 ->", ch.captcha_image_path, "session:", ch.challenge_id,
        flush=True)

  print("[2] captcha_answer.txt 대기...", flush=True)
  answer = None
  for _ in range(150):
    if os.path.exists(ANSWER_FILE):
      with open(ANSWER_FILE, encoding="utf-8") as f:
        answer = f.read().strip()
      if answer:
        break
    await asyncio.sleep(2)
  if not answer:
    print("[!] 답안 없음, 종료", flush=True)
    await manager.shutdown()
    return

  print(f"[3] 답안 {answer!r} 제출 (실패 기대)", flush=True)
  try:
    info = await scourt.submit_answer(ch.challenge_id, answer)
    print("[4] 예상과 다름 — 에러 없이 결과 반환됨:", flush=True)
    print(info.model_dump(), flush=True)
  except ValueError as e:
    print("[4] OK — ValueError 발생:", flush=True)
    print("    ", str(e), flush=True)
  await manager.shutdown()


if __name__ == "__main__":
  asyncio.run(main())
