"""사용자 지정 경매 사건 검증 — 2025타경602 / 순천지원."""
import asyncio, json
from lawyer_mcp import courtauction
from lawyer_mcp.browser import manager
import _common  # noqa: F401 — 임포트만으로 UTF-8 출력 설정

COURT, CASE_NO = "순천지원", "2025타경602"

async def main():
  items = await courtauction.search_by_case(CASE_NO, COURT)
  print(f"[1] search_by_case -> {len(items)}건", flush=True)
  for it in items:
    print("   ", json.dumps(it.model_dump(), ensure_ascii=False), flush=True)

  print("[2] item_detail(첫 물건):", flush=True)
  detail = await courtauction.item_detail(CASE_NO, court=COURT)
  if detail is None:
    print("   None", flush=True)
  else:
    print(json.dumps(detail.model_dump(), ensure_ascii=False, indent=2), flush=True)
  await manager.shutdown()

asyncio.run(main())
