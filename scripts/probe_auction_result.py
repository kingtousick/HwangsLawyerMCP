"""경매 결과 그리드 구조 탐침 — 법원만 지정한 광역 검색.

  uv run python scripts/probe_auction_result.py
실제 결과 테이블의 id·헤더·첫 행들을 덤프해 결과 파싱 셀렉터를 확정하고,
상세 검증에 쓸 실제 사건번호를 확보한다.
"""

import asyncio
import json

from lawyer_mcp import courtauction
from lawyer_mcp.browser import manager
from _common import out

COURT = "서울중앙지방법원"
DUMP_PNG = out("probe_auction_result.png")


async def main():
  async with manager.page() as page:
    await page.goto(courtauction.SEARCH_URL, wait_until="networkidle")
    await page.wait_for_selector(courtauction._SEL_CASE_NO, timeout=20000)
    await asyncio.sleep(2)

    # 법원만 선택하고 사건번호는 비운 채 검색 (광역 조회)
    try:
      await page.select_option(courtauction._SEL_COURT_SELECT, value=COURT)
    except Exception as e:
      print("법원 선택 실패:", e, flush=True)
    await page.click(courtauction._SEL_SEARCH_BTN)
    await page.wait_for_load_state("networkidle")
    await asyncio.sleep(3)

    await page.screenshot(path=DUMP_PNG, full_page=True)
    print("[*] 스크린샷 ->", DUMP_PNG, flush=True)

    # 페이지 내 모든 table id + 행/열 구조 덤프
    tables = await page.evaluate(
      """() => {
        const txt = (el) => (el.innerText || '').trim().replace(/\\s+/g, ' ');
        return [...document.querySelectorAll('table')].map(tb => {
          const rows = [...tb.querySelectorAll('tr')].slice(0, 6).map(tr =>
            [...tr.querySelectorAll('th,td')].map(txt));
          return {
            id: tb.id || null,
            rowCount: tb.querySelectorAll('tr').length,
            sample: rows.filter(r => r.some(x => x)),
          };
        }).filter(t => t.rowCount > 0);
      }"""
    )
    print(json.dumps(tables, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
  asyncio.run(main())
