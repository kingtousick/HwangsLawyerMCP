"""실조회 끝까지: 폼→CAPTCHA 저장→답안 파일 대기→제출→결과 DOM 덤프.

같은 페이지/세션을 유지하기 위해 한 프로세스에서 처리한다.
  1) 폼 채우고 result_captcha.png 저장
  2) captcha_answer.txt 가 생길 때까지 폴링(최대 5분)
  3) 답안 입력 후 검색 → 결과 영역 DOM/텍스트/스크린샷 덤프
"""

import asyncio
import json
import os

from playwright.async_api import async_playwright
from _common import out

# 실제 사건 정보는 저장소에 두지 않는다. 환경변수로 주입해 사용한다.
COURT = os.environ.get("LAWYER_MCP_TEST_COURT", "○○시법원")
YEAR = os.environ.get("LAWYER_MCP_TEST_YEAR", "2025")
DIV = os.environ.get("LAWYER_MCP_TEST_DIV", "자")
SERIAL = os.environ.get("LAWYER_MCP_TEST_SERIAL", "10000")
PARTY = os.environ.get("LAWYER_MCP_TEST_PARTY", "홍길동")
UA = (
  "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
ANSWER_FILE = out("captcha_answer.txt")

S = {
  "court": "select[id$='_sbx_cortCd']",
  "year": "select[id$='_sbx_csYr']",
  "div": "select[id$='_sbx_csDvsCd']",
  "serial": "input[id$='_ibx_csSerial']",
  "party": "input[id$='_ibx_btprNm']",
  "cap_img": "img[id$='_img_captcha']",
  "cap_in": "input[id$='_ibx_answer']",
  "submit": "input[id$='_btn_srchCs']",
}


async def dump_dom(page):
  """결과 화면의 보이는 텍스트/표 구조를 수집."""
  return await page.evaluate(
    """() => {
      const out = {tables: [], dlists: [], alerts: []};
      // 경고/안내 텍스트(검색 실패 등)
      for (const el of document.querySelectorAll('[id*="msg"],[class*="message"],[role="alert"]')) {
        const t = (el.innerText||'').trim();
        if (t) out.alerts.push(t.slice(0,200));
      }
      // 모든 table 의 id 와 행/셀 텍스트
      for (const tb of document.querySelectorAll('table')) {
        const rows = [...tb.querySelectorAll('tr')].map(tr =>
          [...tr.querySelectorAll('th,td')].map(c => (c.innerText||'').trim())
        ).filter(r => r.some(x => x));
        if (rows.length) out.tables.push({id: tb.id||null, rows: rows.slice(0, 40)});
      }
      return out;
    }"""
  )


async def main():
  if os.path.exists(ANSWER_FILE):
    os.remove(ANSWER_FILE)

  async with async_playwright() as p:
    browser = await p.chromium.launch(headless=True)
    ctx = await browser.new_context(user_agent=UA, locale="ko-KR",
                                    viewport={"width": 1440, "height": 1000})
    page = await ctx.new_page()
    await page.goto("https://ssgo.scourt.go.kr/", wait_until="networkidle")
    await page.wait_for_selector(S["serial"], timeout=20000)

    await page.select_option(S["court"], value=COURT)
    await page.select_option(S["year"], value=YEAR)
    await page.select_option(S["div"], value=DIV)
    await page.fill(S["serial"], SERIAL)
    await page.fill(S["party"], PARTY)
    await page.wait_for_selector(S["cap_img"], timeout=10000)
    await page.locator(S["cap_img"]).first.screenshot(path=out("result_captcha.png"))
    print("[1] 폼 입력 완료, CAPTCHA 저장 -> result_captcha.png", flush=True)

    # [2] 답안 대기
    print("[2] captcha_answer.txt 대기 중...", flush=True)
    answer = None
    for _ in range(150):  # 최대 ~5분
      if os.path.exists(ANSWER_FILE):
        with open(ANSWER_FILE, encoding="utf-8") as f:
          answer = f.read().strip()
        if answer:
          break
      await asyncio.sleep(2)
    if not answer:
      print("[!] 답안 미입력으로 종료", flush=True)
      await browser.close()
      return
    print(f"[3] 답안 수신: {answer!r}, 제출", flush=True)

    await page.fill(S["cap_in"], answer)
    await page.click(S["submit"])
    await page.wait_for_load_state("networkidle")
    await asyncio.sleep(2)  # 결과 렌더 여유

    await page.screenshot(path=out("result_page.png"), full_page=True)
    dom = await dump_dom(page)
    with open(out("result_dom.json"), "w", encoding="utf-8") as f:
      json.dump(dom, f, ensure_ascii=False, indent=2)
    print("[4] 결과 저장 -> result_page.png, result_dom.json", flush=True)
    print("ALERTS:", json.dumps(dom["alerts"], ensure_ascii=False), flush=True)
    print(f"TABLES: {len(dom['tables'])}개", flush=True)
    await browser.close()


if __name__ == "__main__":
  asyncio.run(main())
