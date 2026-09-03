"""경매사건검색 결과 구조 탐침 — 2025타경602 순천지원."""
import asyncio, json
from lawyer_mcp.browser import manager
from _common import out

URL = "https://www.courtauction.go.kr/pgj/index.on?w2xPath=/pgj/ui/pgj100/PGJ159M00.xml"
PNG = out("probe_case_result.png")

async def main():
  msgs = []
  async with manager.page() as page:
    page.on("dialog", lambda d: (msgs.append(d.message), asyncio.create_task(d.accept())))
    await page.goto(URL, wait_until="networkidle")
    await page.wait_for_selector("input[id$='_ibx_auctnCsSrchCsNo']", timeout=20000)
    await asyncio.sleep(1)

    # 순천지원 옵션 확인
    courts = await page.evaluate(
      """() => [...document.querySelector("select[id$='_sbx_auctnCsSrchCortOfc']").options]
                .map(o=>o.value).filter(v=>v.includes('순천'))"""
    )
    print("순천 옵션:", courts, flush=True)
    await page.select_option("select[id$='_sbx_auctnCsSrchCortOfc']", value=courts[0] if courts else "순천지원")
    await page.select_option("select[id$='_sbx_auctnCsSrchCsYear']", value="2025")
    await page.fill("input[id$='_ibx_auctnCsSrchCsNo']", "602")
    await page.click("input[id$='_btn_auctnCsSrchBtn']")
    await page.wait_for_load_state("networkidle")
    await asyncio.sleep(4)
    print("alert:", msgs, flush=True)
    await page.screenshot(path=PNG, full_page=True)

    tables = await page.evaluate(
      """() => {
        const txt=el=>(el.innerText||'').trim().replace(/\s+/g,' ');
        return [...document.querySelectorAll('table')].map(tb=>({
          id: tb.id||null, rows: tb.querySelectorAll('tr').length,
          head: txt(tb).slice(0,140)
        })).filter(t=>t.id && t.rows>0);
      }"""
    )
    print(json.dumps(tables, ensure_ascii=False, indent=2), flush=True)

asyncio.run(main())
