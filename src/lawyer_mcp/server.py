"""법원 경매/사건검색 MCP 서버.

FastMCP 로 5개 툴을 노출한다:
  - auction_case_search    : 경매 '사건' 조회(법원+사건번호) — 미종국/취하 포함
  - auction_search_by_case : 경매 '진행 중 매각물건' 목록 검색
  - auction_item_detail    : 경매 진행 물건 상세(기일내역)
  - case_search_captcha    : 나의 사건검색 1단계 (CAPTCHA 이미지)
  - case_search_submit     : 나의 사건검색 2단계 (CAPTCHA 입력 후 조회)
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from mcp.server.fastmcp import FastMCP, Image

from . import courtauction, scourt
from .browser import manager


@asynccontextmanager
async def _lifespan(_server: FastMCP) -> AsyncIterator[None]:
  """서버가 내려갈 때 브라우저를 같은 이벤트 루프에서 정리한다.

  mcp.run() 이 반환된 뒤에는 이벤트 루프가 이미 닫혀 있어서, 그 시점에
  anyio.run() 으로 새 루프를 열어 Playwright 객체를 닫으려 하면 실패한다
  (객체가 원래 루프에 묶여 있기 때문). lifespan 안에서 정리하면 서버와 같은
  루프에서 실행돼 실제로 닫힌다.
  """
  try:
    yield
  finally:
    await manager.shutdown()


mcp = FastMCP("lawyer-mcp", lifespan=_lifespan)


@mcp.tool()
async def auction_case_search(case_no: str, court: str) -> dict | None:
  """법원경매 '사건'을 사건번호로 조회한다(경매사건검색).

  날짜 필터가 없어 진행 중·미종국·취하·종국 사건까지 바로 조회된다.
  사건 기본정보·물건목록·당사자·목록(소재지)을 함께 반환한다. 특정 사건번호
  조회에는 auction_search_by_case 보다 이 툴을 우선 사용한다.

  Args:
    case_no: 사건번호 (예: '2025타경602').
    court: 법원명. 지원은 짧은 이름(예: '순천지원'), 본원은 '서울중앙지방법원'.

  Returns:
    사건 종합 정보. 사건을 찾지 못하면 None.
  """
  case = await courtauction.case_search(case_no, court)
  return case.model_dump() if case else None


@mcp.tool()
async def auction_search_by_case(case_no: str, court: str | None = None) -> list[dict]:
  """법원경매 '진행 중 매각물건'을 사건번호로 검색한다(물건상세검색).

  매각기일이 설정된 부동산 물건만 나온다. 미종국/취하 등 진행물건이 없는
  사건은 빈 리스트가 된다(그 경우 auction_case_search 를 사용).

  Args:
    case_no: 사건번호 (예: '2024타경12345').
    court: 관할 법원명 (선택, 예: '서울중앙지방법원').

  Returns:
    물건 요약 정보 리스트. 결과가 없으면 빈 리스트.
  """
  items = await courtauction.search_by_case(case_no, court)
  return [it.model_dump() for it in items]


@mcp.tool()
async def auction_item_detail(
  case_no: str, item_no: str | None = None, court: str | None = None
) -> dict | None:
  """법원경매 물건의 상세 정보(감정가/최저가/기일 내역)를 조회한다.

  Args:
    case_no: 사건번호 (예: '2024타경12345').
    item_no: 물건번호 (선택). 미지정 시 첫 번째 물건.
    court: 관할 법원명 (선택).

  Returns:
    물건 상세 정보. 없으면 None.
  """
  detail = await courtauction.item_detail(case_no, item_no, court)
  return detail.model_dump() if detail else None


@mcp.tool()
async def case_search_captcha(
  court: str,
  case_no: str,
  party_name: str,
):
  """[1단계] 나의 사건검색을 시작하고 CAPTCHA 이미지를 반환한다.

  CAPTCHA 이미지를 **인라인 이미지 콘텐츠로 직접 반환**하므로, 호출한 모델이
  이미지를 그대로 보고 문자를 읽어 case_search_submit 의 captcha_text 로 넘기면
  된다. (별도 파일 열람·파일시스템 접근이 필요 없어 Cowork/데스크탑 등 어떤
  MCP 클라이언트에서도 동일하게 동작한다.) 호환을 위해 저장된 파일 경로도
  함께 돌려준다.

  Args:
    court: 법원명 (예: '여수시법원'). 사이트 select 옵션과 정확히 일치해야 함.
    case_no: 사건번호 (예: '25자10000'). 사건구분은 여기서 자동 파싱.
    party_name: 당사자명. ssgo 사건검색은 당사자명이 필수입력이다.

  Returns:
    [CAPTCHA 이미지, {session_id, captcha_image_path, message}] 의 리스트.
    이미지는 인라인 이미지 콘텐츠, 나머지는 JSON 텍스트로 전달된다.
  """
  challenge = await scourt.start_challenge(court, case_no, party_name)
  return [Image(path=challenge.captcha_image_path), challenge.model_dump()]


@mcp.tool()
async def case_search_submit(session_id: str, captcha_text: str) -> dict:
  """[2단계] CAPTCHA 값을 입력해 사건 조회를 완료한다.

  Args:
    session_id: case_search_captcha 가 반환한 세션 ID.
    captcha_text: 사용자가 이미지에서 읽은 문자.

  Returns:
    사건 기본정보와 진행/기일 내역.
  """
  info = await scourt.submit_answer(session_id, captcha_text)
  return info.model_dump()


def main() -> None:
  """stdio 트랜스포트로 MCP 서버를 실행한다.

  브라우저 정리는 _lifespan 이 담당한다.
  """
  mcp.run()


if __name__ == "__main__":
  main()
