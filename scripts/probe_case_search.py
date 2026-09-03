"""경매사건검색 탭 폼 구조 탐침 + 2025타경602 순천지원 조회 시도."""
import asyncio, json
from lawyer_mcp.browser import manager
from _common import out

NAV = "https://www.courtauction.go.kr/pgj/index.on"
PNG = out("probe_case_search.png")

async def main():
  async with manager.page() as page:
    await page.goto(NAV, wait_until="networkidle")
    await asyncio.sleep(2)
    # 경매사건검색 네비게이션 클릭
    await page.click("a[id$='_anc_auctnCsSrch']")
    await page.wait_for_load_state("networkidle")
    await asyncio.sleep(3)
    print("url:", page.url, flush=True)
    await page.screenshot(path=PNG, full_page=True)

    info = await page.evaluate(
      """() => {
        const pick=el=>({tag:el.tagName.toLowerCase(),id:el.id||null,
          title:el.getAttribute('title')||null,type:el.getAttribute('type')||null,
          value:el.value||null, optCount: el.options?el.options.length:null,
          opts: el.options?[...el.options].slice(0,5).map(o=>o.value):null});
        return {
          selects:[...document.querySelectorAll('select')].map(pick),
          inputs:[...document.querySelectorAll('input')].filter(i=>i.type!=='hidden').map(pick),
          buttons:[...document.querySelectorAll('input[type=button],button')]
            .map(b=>({id:b.id||null,val:b.value||null,title:b.getAttribute('title')||null}))
            .filter(b=>b.val||b.title),
        };
      }"""
    )
    print(json.dumps(info, ensure_ascii=False, indent=2), flush=True)

asyncio.run(main())
