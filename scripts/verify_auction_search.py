"""경매 search_by_case 검증 + 상세 페이지 구조 탐침.

  uv run python scripts/verify_auction_search.py
"""

import asyncio
import json

from lawyer_mcp import courtauction
from lawyer_mcp.browser import manager
from _common import out

COURT, CASE_NO = "서울중앙지방법원", "2008타경25092"
DETAIL_PNG = out("probe_auction_detail.png")


async def main():
  # 1) 목록 검색 검증
  items = await courtauction.search_by_case(CASE_NO, COURT)
  print(f"[1] search_by_case -> {len(items)}건", flush=True)
  for it in items[:3]:
    print("   ", json.dumps(it.model_dump(), ensure_ascii=False), flush=True)

  # 2) 상세 페이지 구조 탐침 (물건 1번 클릭)
  async with manager.page() as page:
    await courtauction._fill_and_search(page, CASE_NO, COURT)
    await asyncio.sleep(2)

    # 결과 그리드 첫 물건의 사건번호 링크를 클릭한다.
    tb_sel = f"table[id$='{courtauction._RESULT_GRID_SUFFIX}']"
    # 사건번호 셀(2번째 td) 안의 클릭 요소(a/nobr/span) 탐색
    link = page.locator(f"{tb_sel} tbody tr td:nth-child(2)").first
    print("[2] 사건번호 셀 클릭 시도...", flush=True)
    try:
      await link.click()
      await page.wait_for_load_state("networkidle")
      await asyncio.sleep(3)
    except Exception as e:
      print("   클릭 실패:", e, flush=True)

    await page.screenshot(path=DETAIL_PNG, full_page=True)
    print("   상세 스크린샷 ->", DETAIL_PNG, flush=True)
    print("   url:", page.url, flush=True)

    tables = await page.evaluate(
      """() => {
        const txt = (el) => (el.innerText || '').trim().replace(/\\s+/g, ' ');
        return [...document.querySelectorAll('table')].map(tb => ({
          id: tb.id || null,
          rowCount: tb.querySelectorAll('tr').length,
          head: txt(tb).slice(0, 120),
        })).filter(t => t.rowCount > 0 && t.id);
      }"""
    )
    print("[3] 상세 페이지 table 목록:", flush=True)
    print(json.dumps(tables, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
  asyncio.run(main())
