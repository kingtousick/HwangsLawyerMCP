"""scourt 모듈의 폼 입력 셀렉터를 실제 사건으로 검증(검색 직전까지).

  uv run python scripts/verify_scourt.py
"""

import asyncio
import os

from lawyer_mcp import scourt
from lawyer_mcp.browser import manager
from _common import out

# 실제 사건 정보는 저장소에 두지 않는다. 환경변수로 주입해 사용한다.
COURT = os.environ.get("LAWYER_MCP_TEST_COURT", "○○시법원")
CASE_NO = os.environ.get("LAWYER_MCP_TEST_CASE_NO", "25자10000")
PARTY = "테스트"  # 당사자명 필수 → 더미값(검색은 실행 안 함)


async def main():
  year, div, serial = scourt.parse_case_no(CASE_NO)
  print(f"파싱: 연도={year} 사건구분={div} 일련번호={serial}")

  ctx, page = await manager.new_persistent_page()
  await page.goto(scourt.SEARCH_URL, wait_until="networkidle")
  await page.wait_for_selector(scourt._SEL_SERIAL, timeout=20000)

  # 옵션 존재 확인
  courts = await page.locator(scourt._SEL_COURT + " option").all_inner_texts()
  divs = await page.locator(scourt._SEL_DIVISION + " option").all_inner_texts()
  print(f"법원 '{COURT}' 옵션 존재:", COURT in [c.strip() for c in courts])
  print(f"사건구분 '{div}' 옵션 존재:", div in [d.strip() for d in divs])

  # 실제 입력
  await scourt._select_by_value_or_label(page, scourt._SEL_COURT, COURT)
  await scourt._select_by_value_or_label(page, scourt._SEL_YEAR, year)
  await scourt._select_by_value_or_label(page, scourt._SEL_DIVISION, div)
  await page.fill(scourt._SEL_SERIAL, serial)
  await page.fill(scourt._SEL_PARTY, PARTY)

  # 입력값 되읽어 검증
  got_court = await page.locator(scourt._SEL_COURT).input_value()
  got_year = await page.locator(scourt._SEL_YEAR).input_value()
  got_div = await page.locator(scourt._SEL_DIVISION).input_value()
  got_serial = await page.locator(scourt._SEL_SERIAL).input_value()
  got_party = await page.locator(scourt._SEL_PARTY).input_value()
  print("폼 상태 -> 법원:", got_court, "| 연도:", got_year,
        "| 구분:", got_div, "| 일련:", got_serial, "| 당사자:", got_party)

  # CAPTCHA 캡처 검증
  cap = page.locator(scourt._SEL_CAPTCHA_IMG).first
  await cap.screenshot(path=out("verify_captcha.png"))
  box = await cap.bounding_box()
  print("CAPTCHA 캡처 OK -> verify_captcha.png, 크기:", box)

  ok = (got_court == COURT and got_year == year and got_div == div
        and got_serial == serial and got_party == PARTY)
  print("\n검증 결과:", "PASS ✅" if ok else "FAIL ❌")

  await ctx.close()
  await manager.shutdown()


if __name__ == "__main__":
  asyncio.run(main())
