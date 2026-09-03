"""Playwright 브라우저 수명 관리.

WebSquare 기반 법원 사이트는 JS 렌더링이 필수라 헤드리스 브라우저로 조작한다.
브라우저 인스턴스는 무겁기 때문에 프로세스당 하나만 띄워 재사용한다.
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from playwright.async_api import Browser, BrowserContext, Page, async_playwright

# 정부 사이트는 봇 차단이 있어 일반적인 데스크톱 UA로 위장한다.
_USER_AGENT = (
  "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
  "AppleWebKit/537.36 (KHTML, like Gecko) "
  "Chrome/124.0.0.0 Safari/537.36"
)

# HEADLESS 환경변수로 디버깅 시 브라우저를 띄워 볼 수 있다.
import os

_HEADLESS = os.environ.get("LAWYER_MCP_HEADLESS", "1") != "0"


class BrowserManager:
  """단일 브라우저 인스턴스를 lazy 하게 생성/재사용한다."""

  def __init__(self) -> None:
    self._playwright = None
    self._browser: Browser | None = None
    self._lock = asyncio.Lock()

  async def _ensure_browser(self) -> Browser:
    async with self._lock:
      if self._browser is None or not self._browser.is_connected():
        if self._playwright is None:
          self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=_HEADLESS)
      return self._browser

  @asynccontextmanager
  async def page(self):
    """요청 1건당 격리된 컨텍스트/페이지를 만들어 사용 후 정리한다."""
    browser = await self._ensure_browser()
    context: BrowserContext = await browser.new_context(
      user_agent=_USER_AGENT,
      locale="ko-KR",
      viewport={"width": 1440, "height": 900},
    )
    page: Page = await context.new_page()
    try:
      yield page
    finally:
      await context.close()

  async def new_persistent_page(self) -> tuple[BrowserContext, Page]:
    """CAPTCHA 흐름처럼 2단계에 걸쳐 세션을 유지해야 할 때 사용.

    호출자가 직접 context.close() 로 정리할 책임을 진다.
    """
    browser = await self._ensure_browser()
    context = await browser.new_context(
      user_agent=_USER_AGENT,
      locale="ko-KR",
      viewport={"width": 1440, "height": 900},
    )
    page = await context.new_page()
    return context, page

  async def shutdown(self) -> None:
    if self._browser is not None:
      await self._browser.close()
      self._browser = None
    if self._playwright is not None:
      await self._playwright.stop()
      self._playwright = None


# 모듈 전역 싱글턴
manager = BrowserManager()
