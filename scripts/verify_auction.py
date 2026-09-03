"""경매 프로덕션 함수 전체 검증 — search_by_case + item_detail.

  uv run python scripts/verify_auction.py
"""

import asyncio
import json

from lawyer_mcp import courtauction
from lawyer_mcp.browser import manager
import _common  # noqa: F401 — 임포트만으로 UTF-8 출력 설정

COURT, CASE_NO = "서울중앙지방법원", "2008타경25092"


async def main():
  items = await courtauction.search_by_case(CASE_NO, COURT)
  print(f"[1] search_by_case -> {len(items)}건", flush=True)
  for it in items[:3]:
    print("   ", json.dumps(it.model_dump(), ensure_ascii=False), flush=True)

  print("[2] item_detail(물건 1번):", flush=True)
  detail = await courtauction.item_detail(CASE_NO, item_no="1", court=COURT)
  if detail is None:
    print("   None 반환", flush=True)
  else:
    print(json.dumps(detail.model_dump(), ensure_ascii=False, indent=2), flush=True)

  await manager.shutdown()


if __name__ == "__main__":
  asyncio.run(main())
