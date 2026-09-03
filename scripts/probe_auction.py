"""법원경매정보 물건상세검색 폼 구조 탐침.

  uv run python scripts/probe_auction.py
실제 select/input/button 의 id·라벨·placeholder 를 덤프해 셀렉터를 확정한다.
"""

import asyncio
import json

from lawyer_mcp import courtauction
from lawyer_mcp.browser import manager
from _common import out

DUMP_PNG = out("probe_auction.png")


async def main():
  async with manager.page() as page:
    await page.goto(courtauction.SEARCH_URL, wait_until="networkidle")
    await asyncio.sleep(3)  # WebSquare 렌더 대기

    await page.screenshot(path=DUMP_PNG, full_page=True)
    print("[*] 스크린샷 ->", DUMP_PNG, flush=True)

    info = await page.evaluate(
      """() => {
        const pick = (el) => ({
          tag: el.tagName.toLowerCase(),
          id: el.id || null,
          name: el.getAttribute('name') || null,
          type: el.getAttribute('type') || null,
          placeholder: el.getAttribute('placeholder') || null,
          title: el.getAttribute('title') || null,
          value: el.value || null,
          text: (el.innerText || '').trim().slice(0, 30) || null,
        });
        const inAnyFrame = (sel) =>
          [...document.querySelectorAll(sel)].map(pick);
        return {
          url: location.href,
          selects: [...document.querySelectorAll('select')].map(s => ({
            ...pick(s),
            options: [...s.options].slice(0, 8).map(o => ({v: o.value, t: o.text})),
            optionCount: s.options.length,
          })),
          inputs: inAnyFrame('input').filter(i =>
            i.type !== 'hidden'),
          buttons: inAnyFrame('button, a[href], input[type=button], input[type=submit]')
            .filter(b => b.text || b.value).slice(0, 40),
          iframes: [...document.querySelectorAll('iframe')].map(f => ({
            id: f.id || null, src: f.src || null,
          })),
        };
      }"""
    )
    print(json.dumps(info, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
  asyncio.run(main())
