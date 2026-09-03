"""나의 사건검색(ssgo.scourt.go.kr) 페이지의 실제 DOM 구조를 떠서 셀렉터 파악.

  uv run python scripts/probe_scourt.py
"""

import asyncio
import json

from playwright.async_api import async_playwright
from _common import out

CANDIDATE_URLS = [
  "https://ssgo.scourt.go.kr/",
]


async def inventory(frame):
  return await frame.evaluate(
    """() => {
      const pick = (el) => ({
        tag: el.tagName.toLowerCase(),
        id: el.id || null,
        name: el.getAttribute('name'),
        type: el.getAttribute('type'),
        placeholder: el.getAttribute('placeholder'),
        title: el.getAttribute('title'),
        ariaLabel: el.getAttribute('aria-label'),
        text: (el.innerText || el.value || '').trim().slice(0, 40) || null,
        src: el.getAttribute('src'),
        opts: el.tagName.toLowerCase() === 'select'
          ? [...el.options].slice(0, 12).map(o => o.text.trim() + '=' + o.value)
          : undefined,
      });
      const sel = 'input,select,button,a[onclick],img[id],img[src*="captcha"],img[src*="Captcha"],iframe';
      return [...document.querySelectorAll(sel)].map(pick);
    }"""
  )


async def main():
  async with async_playwright() as p:
    browser = await p.chromium.launch(headless=True)
    ctx = await browser.new_context(
      user_agent=(
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
      ),
      locale="ko-KR",
    )
    page = await ctx.new_page()

    for url in CANDIDATE_URLS:
      print("\n" + "=" * 70)
      print("URL:", url)
      try:
        resp = await page.goto(url, wait_until="networkidle", timeout=40000)
        print("status:", resp.status if resp else None)
        print("final URL:", page.url)
        print("title:", await page.title())
      except Exception as e:
        print("  ERROR:", repr(e))
        continue

      # 메인 + 모든 프레임 조사
      for fi, frame in enumerate(page.frames):
        try:
          items = await inventory(frame)
        except Exception as e:
          print(f"  frame[{fi}] inventory error:", repr(e))
          continue
        relevant = [
          it for it in items
          if it["tag"] in ("input", "select", "iframe")
          or (it["tag"] == "img" and (it.get("src") or "").lower().find("captcha") >= 0)
          or (it["tag"] == "img" and it.get("id"))
          or (it["text"] and it["tag"] in ("button", "a"))
        ]
        if not relevant:
          continue
        print(f"\n  --- frame[{fi}] url={frame.url} ({len(items)} elements) ---")
        for it in relevant:
          it = {k: v for k, v in it.items() if v not in (None, [])}
          print("   ", json.dumps(it, ensure_ascii=False))

      # 디버그용 스크린샷
      await page.screenshot(path=out("probe_ssgo.png"), full_page=True)
      print("\n  screenshot -> probe_ssgo.png")

    await browser.close()


if __name__ == "__main__":
  asyncio.run(main())
