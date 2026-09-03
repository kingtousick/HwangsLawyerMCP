"""특정 사건번호 검색 결과의 행 구조를 정밀 덤프 — 컬럼 매핑 확정용.

  uv run python scripts/probe_auction_rows.py
각 tr 의 th/td 구분과 전체 셀 텍스트(자르지 않음)를 출력한다.
"""

import asyncio
import json

from lawyer_mcp import courtauction
from lawyer_mcp.browser import manager
from _common import out

COURT, CASE_NO = "서울중앙지방법원", "2008타경25092"
DUMP_PNG = out("probe_auction_rows.png")


async def main():
  async with manager.page() as page:
    await courtauction._fill_and_search(page, CASE_NO, COURT)
    await asyncio.sleep(3)
    await page.screenshot(path=DUMP_PNG, full_page=True)
    print("[*] 스크린샷 ->", DUMP_PNG, flush=True)

    data = await page.evaluate(
      """() => {
        const txt = (el) => (el.innerText || '').trim().replace(/\\s+/g, ' ');
        const tb = [...document.querySelectorAll('table')]
          .find(t => t.id && t.id.endsWith('_grd_gdsDtlSrchResult_body_table'));
        if (!tb) return {found: false};
        const rows = [...tb.querySelectorAll('tr')].map(tr => ({
          tag: [...tr.children].map(c => c.tagName.toLowerCase()).join(','),
          cells: [...tr.querySelectorAll('th,td')].map(c => ({
            t: txt(c),
            colspan: c.getAttribute('colspan') || null,
            rowspan: c.getAttribute('rowspan') || null,
          })),
        }));
        return {found: true, id: tb.id, rows};
      }"""
    )
    print(json.dumps(data, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
  asyncio.run(main())
