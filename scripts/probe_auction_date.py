"""기간 필터 확장 + 법원 옵션 확인 후 사건번호 검색 탐침."""
import asyncio, json
from lawyer_mcp import courtauction
from lawyer_mcp.browser import manager
import _common  # noqa: F401 — 임포트만으로 UTF-8 출력 설정

CASE_NO = "2025타경602"

async def main():
  async with manager.page() as page:
    await page.goto(courtauction.SEARCH_URL, wait_until="networkidle")
    await page.wait_for_selector(courtauction._SEL_CASE_NO, timeout=20000)
    await asyncio.sleep(2)

    # 1) '순천' 포함 법원 옵션 확인
    courts = await page.evaluate(
      """() => [...document.querySelector("select[id$='_sbx_rletCortOfc']").options]
                .map(o=>o.value).filter(v=>v.includes('순천'))"""
    )
    print("[1] '순천' 법원 옵션:", courts, flush=True)
    court = courts[0] if courts else "순천지원"

    await page.select_option(courtauction._SEL_COURT_SELECT, value=court)
    await page.select_option(courtauction._SEL_CASE_YEAR, value="2025")
    await page.fill(courtauction._SEL_CASE_NO, "602")

    # 2) 매각기간을 넓게 설정 (과거~미래)
    for sel, val in [
      ("input[id$='_cal_rletPerdStr_input']", "2000.01.01"),
      ("input[id$='_cal_rletPerdEnd_input']", "2030.12.31"),
    ]:
      try:
        await page.fill(sel, "")
        await page.fill(sel, val)
      except Exception as e:
        print("   날짜 입력 실패", sel, e, flush=True)

    await page.click(courtauction._SEL_SEARCH_BTN)
    await page.wait_for_load_state("networkidle")
    await asyncio.sleep(3)

    # 3) 검색조건 요약 + 결과 행 수
    summary = await page.evaluate(
      """() => {
        const tb=[...document.querySelectorAll('table')].find(t=>t.id&&t.id.endsWith('_grd_gdsDtlSrchResult_body_table'));
        const cond=[...document.querySelectorAll('table')].map(t=>(t.innerText||'').trim()).find(s=>s.includes('검색조건'));
        const tds = tb ? [...tb.querySelectorAll('tr')].filter(tr=>tr.querySelectorAll('td').length>=8).length : -1;
        return {cond: cond ? cond.replace(/\s+/g,' ').slice(0,200): null, itemRows: tds};
      }"""
    )
    print("[2] 검색조건:", summary["cond"], flush=True)
    print("[3] 물건 행 수:", summary["itemRows"], flush=True)

asyncio.run(main())
