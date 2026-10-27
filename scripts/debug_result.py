"""결과 페이지 진단 — 제출 후 실제 페이지 텍스트/스크린샷을 덤프한다.

  uv run python scripts/debug_result.py
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
DUMP_TXT = out("result_page.txt")
DUMP_PNG = out("result_page.png")


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

  sess = scourt._sessions[ch.challenge_id]
  page = sess.page
  print(f"[3] 답안 {answer!r} 제출", flush=True)
  await page.fill(scourt._SEL_CAPTCHA_INPUT, answer)
  await page.click(scourt._SEL_SUBMIT)
  await page.wait_for_load_state("networkidle")
  await asyncio.sleep(2)

  # 전체 페이지 텍스트 + 스크린샷 덤프
  body_text = await page.evaluate("() => document.body.innerText")
  with open(DUMP_TXT, "w", encoding="utf-8") as f:
    f.write(body_text)
  await page.screenshot(path=DUMP_PNG, full_page=True)
  print("[4] 페이지 텍스트 ->", DUMP_TXT, flush=True)
  print("[4] 스크린샷 ->", DUMP_PNG, flush=True)

  # 페이지에 존재하는 table id 목록도 출력
  table_ids = await page.evaluate(
    "() => [...document.querySelectorAll('table')].map(t => t.id).filter(Boolean)"
  )
  print("[5] table ids:", flush=True)
  print(json.dumps(table_ids, ensure_ascii=False, indent=2), flush=True)

  await manager.shutdown()


if __name__ == "__main__":
  asyncio.run(main())
