"""경매사건검색 case_search 검증 — 2025타경602 순천지원."""
import asyncio, json
from lawyer_mcp import courtauction
from lawyer_mcp.browser import manager
import _common  # noqa: F401 — 임포트만으로 UTF-8 출력 설정

async def main():
  case = await courtauction.case_search("2025타경602", "순천지원")
  if case is None:
    print("None 반환", flush=True)
  else:
    print(json.dumps(case.model_dump(), ensure_ascii=False, indent=2), flush=True)
  # 없는 사건
  none_case = await courtauction.case_search("2025타경999999", "순천지원")
  print("없는 사건 ->", none_case, "(None 기대)", flush=True)
  await manager.shutdown()

asyncio.run(main())
