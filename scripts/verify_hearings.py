"""기일내역(hearings) 그리드 검증 — 실사건 1건으로 그리드 파싱을 확인한다.

  uv run python scripts/verify_hearings.py
파일 기반 CAPTCHA 핸드오프: start_challenge 가 저장한 이미지를 사람이 읽어
captcha_answer.txt 에 기록하면 submit_answer 를 호출한다.
"""

import asyncio
import json
import os

from lawyer_mcp import scourt
from lawyer_mcp.browser import manager
from _common import out

# 실제 사건 정보는 저장소에 두지 않는다. 환경변수로 주입해 사용한다.
COURT = os.environ.get("LAWYER_MCP_TEST_COURT", "○○시법원")
CASE_NO = os.environ.get("LAWYER_MCP_TEST_CASE_NO", "25자10000")
PARTY = os.environ.get("LAWYER_MCP_TEST_PARTY", "홍길동")
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

  print(f"[3] 답안 {answer!r} 제출", flush=True)
  info = await scourt.submit_answer(ch.challenge_id, answer)
  print("[4] 결과:", flush=True)
  print(json.dumps(info.model_dump(), ensure_ascii=False, indent=2), flush=True)
  await manager.shutdown()


if __name__ == "__main__":
  asyncio.run(main())
