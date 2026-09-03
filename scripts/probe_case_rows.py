"""경매사건검색 핵심 테이블 셀 구조 정밀 덤프."""
import asyncio, json
from lawyer_mcp.browser import manager
import _common  # noqa: F401 — 임포트만으로 UTF-8 출력 설정

URL = "https://www.courtauction.go.kr/pgj/index.on?w2xPath=/pgj/ui/pgj100/PGJ159M00.xml"

async def main():
  async with manager.page() as page:
    await page.goto(URL, wait_until="networkidle")
    await page.wait_for_selector("input[id$='_ibx_auctnCsSrchCsNo']", timeout=20000)
    await asyncio.sleep(1)
    await page.select_option("select[id$='_sbx_auctnCsSrchCortOfc']", value="순천지원")
    await page.select_option("select[id$='_sbx_auctnCsSrchCsYear']", value="2025")
    await page.fill("input[id$='_ibx_auctnCsSrchCsNo']", "602")
    await page.click("input[id$='_btn_auctnCsSrchBtn']")
    await page.wait_for_load_state("networkidle")
    await asyncio.sleep(4)

    data = await page.evaluate(
      """() => {
        const txt=el=>(el.innerText||'').trim().replace(/\s+/g,' ');
        const dump=(suffix)=>{
          const tb=[...document.querySelectorAll('table')].find(t=>t.id&&t.id.endsWith(suffix));
          if(!tb) return null;
          return {id: tb.id, rows: [...tb.querySelectorAll('tr')].map(tr=>
            [...tr.querySelectorAll('th,td')].map(c=>({t:txt(c),
              th:c.tagName==='TH'||null})))};
        };
        return {
          basic: dump('_grp_csNoBasDt'),
          goods: dump('_grp_gdsDtsTbl'),
          parties: dump('_grd_ttt_body_table'),
          listing: dump('_wq_uuid_545_body_table'),
        };
      }"""
    )
    print(json.dumps(data, ensure_ascii=False, indent=2), flush=True)

asyncio.run(main())
