"""상세 진입 방법 탐침 — 데이터 행의 클릭 타깃과 팝업/네비게이션 확인.

  uv run python scripts/probe_auction_detail.py
"""

import asyncio
import json

from lawyer_mcp import courtauction
from lawyer_mcp.browser import manager
from _common import out

COURT, CASE_NO = "서울중앙지방법원", "2008타경25092"
DETAIL_PNG = out("probe_auction_detail.png")


async def main():
  async with manager.page() as page:
    await courtauction._fill_and_search(page, CASE_NO, COURT)
    await asyncio.sleep(1)

    # 첫 데이터 행(td 8개) 안의 클릭 후보 요소들을 덤프
    info = await page.evaluate(
      """(suffix) => {
        const txt = (el) => (el.innerText || '').trim().replace(/\\s+/g, ' ');
        const tb = [...document.querySelectorAll('table')]
          .find(t => t.id && t.id.endsWith(suffix));
        const trs = [...tb.querySelectorAll('tr')];
        const dataTr = trs.find(tr => tr.querySelectorAll('td').length >= 8);
        if (!dataTr) return {found: false};
        // 행 안의 a / 클릭가능 요소 수집
        const clickables = [...dataTr.querySelectorAll('a, [onclick], nobr, span')]
          .slice(0, 20)
          .map(el => ({
            tag: el.tagName.toLowerCase(),
            id: el.id || null,
            cls: el.className || null,
            onclick: el.getAttribute('onclick') ? 'Y' : null,
            text: txt(el).slice(0, 30) || null,
          }))
          .filter(e => e.text || e.onclick || e.id);
        return {found: true, html: dataTr.outerHTML.slice(0, 1500), clickables};
      }""",
      courtauction._RESULT_GRID_SUFFIX,
    )
    print("[1] 데이터 행 클릭 후보:", flush=True)
    print(json.dumps(info, ensure_ascii=False, indent=2), flush=True)

    # 팝업/새 페이지 감지 준비
    new_pages = []
    page.context.on("page", lambda p: new_pages.append(p))

    # 사건번호 셀 안의 첫 앵커(a) 클릭 시도
    tb_sel = f"table[id$='{courtauction._RESULT_GRID_SUFFIX}']"
    target = page.locator(f"{tb_sel} tbody tr td a").first
    cnt = await page.locator(f"{tb_sel} tbody tr td a").count()
    print(f"[2] 행 내 a 태그 수: {cnt}", flush=True)
    if cnt:
      print("    첫 a 클릭...", flush=True)
      try:
        await target.click()
        await asyncio.sleep(3)
      except Exception as e:
        print("    클릭 실패:", e, flush=True)

    await asyncio.sleep(1)
    print(f"[3] 메인 url: {page.url}", flush=True)
    print(f"[3] 새 페이지 수: {len(new_pages)}", flush=True)
    detail_page = new_pages[-1] if new_pages else page
    try:
      await detail_page.wait_for_load_state("networkidle")
    except Exception:
      pass
    await detail_page.screenshot(path=DETAIL_PNG, full_page=True)
    print("    상세 url:", detail_page.url, flush=True)

    tables = await detail_page.evaluate(
      """() => {
        const txt = (el) => (el.innerText || '').trim().replace(/\\s+/g, ' ');
        return [...document.querySelectorAll('table')].map(tb => ({
          id: tb.id || null,
          rowCount: tb.querySelectorAll('tr').length,
          head: txt(tb).slice(0, 100),
        })).filter(t => t.id && t.rowCount > 0);
      }"""
    )
    print("[4] 상세 페이지 table 목록:", flush=True)
    print(json.dumps(tables, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
  asyncio.run(main())
