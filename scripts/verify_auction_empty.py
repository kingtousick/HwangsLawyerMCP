"""경매 무결과/엣지 처리 검증."""
import asyncio
from lawyer_mcp import courtauction
from lawyer_mcp.browser import manager
import _common  # noqa: F401 — 임포트만으로 UTF-8 출력 설정

async def main():
  # 1) 유효 연도 + 없는 일련번호 -> 0건 / None
  items = await courtauction.search_by_case("2024타경999999", "서울중앙지방법원")
  print("[1] 없는 사건 search_by_case ->", len(items), "건 (0 기대)", flush=True)
  detail = await courtauction.item_detail("2024타경999999", court="서울중앙지방법원")
  print("[2] 없는 사건 item_detail ->", detail, "(None 기대)", flush=True)
  # 3) 범위 밖 연도 -> 명확한 ValueError
  try:
    await courtauction.search_by_case("2099타경1", "서울중앙지방법원")
    print("[3] 예상과 다름: 에러 없음", flush=True)
  except ValueError as e:
    print("[3] OK ValueError ->", str(e), flush=True)
  await manager.shutdown()

asyncio.run(main())
