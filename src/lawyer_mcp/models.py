"""검색 결과 데이터 모델."""

from __future__ import annotations

from pydantic import BaseModel, Field


class AuctionItem(BaseModel):
  """경매 물건 요약 정보."""

  case_no: str = Field(description="사건번호 (예: 2024타경12345)")
  item_no: str | None = Field(default=None, description="물건번호")
  court: str | None = Field(default=None, description="관할 법원")
  item_type: str | None = Field(default=None, description="물건 종류 (부동산/동산 등)")
  address: str | None = Field(default=None, description="소재지")
  appraisal_value: str | None = Field(default=None, description="감정가")
  min_bid_value: str | None = Field(default=None, description="최저매각가격")
  bid_date: str | None = Field(default=None, description="매각기일")
  status: str | None = Field(default=None, description="진행 상태 (신건/유찰/낙찰 등)")
  detail_url: str | None = Field(default=None, description="물건 상세 페이지 URL")


class AuctionItemDetail(AuctionItem):
  """경매 물건 상세 정보 (기일 내역 포함)."""

  failed_count: int | None = Field(default=None, description="유찰 횟수")
  bid_history: list[dict] = Field(default_factory=list, description="기일별 내역")
  notes: str | None = Field(default=None, description="비고/유의사항")


class AuctionCase(BaseModel):
  """경매사건검색(법원+사건번호) 결과 — 사건 단위 종합 정보.

  물건상세검색과 달리 '진행 중 매각물건'에 한정되지 않아, 미종국·취하·종국
  사건까지 사건번호로 바로 조회된다. 당사자 이름은 사이트에서 마스킹된다.
  """

  court: str | None = Field(default=None, description="관할 법원")
  case_no: str = Field(description="사건번호 (예: 2025타경602)")
  case_name: str | None = Field(default=None, description="사건명 (예: 부동산임의경매)")
  filed_date: str | None = Field(default=None, description="접수일자")
  start_decision_date: str | None = Field(default=None, description="개시결정일자")
  department: str | None = Field(default=None, description="담당계")
  claim_amount: str | None = Field(default=None, description="청구금액")
  final_result: str | None = Field(default=None, description="종국결과 (미종국 등)")
  final_date: str | None = Field(default=None, description="종국일자")
  parties_summary: str | None = Field(
    default=None, description="당사자 요약 (채권자/채무자 등 핵심 당사자명)"
  )
  basic_info: dict[str, str] = Field(
    default_factory=dict, description="사건 기본정보 라벨→값 전체"
  )
  items: list[dict] = Field(
    default_factory=list, description="물건 목록(물건번호/용도/감정가/상태/최근입찰결과)"
  )
  listings: list[dict] = Field(
    default_factory=list, description="목록(소재지/목록구분/비고)"
  )
  parties: list[dict] = Field(default_factory=list, description="당사자(구분/이름)")


class CaseInfo(BaseModel):
  """나의 사건검색 결과 (ssgo.scourt.go.kr 상세 화면 구조 반영).

  당사자 이름은 법원 사이트에서 이미 마스킹된 상태(예: 임OOO)로 제공된다.
  """

  court: str = Field(description="법원")
  case_no: str = Field(description="사건번호")
  case_name: str | None = Field(default=None, description="사건명 (예: [전자]대여금)")
  department: str | None = Field(default=None, description="재판부")
  filed_date: str | None = Field(default=None, description="접수일")
  final_result: str | None = Field(default=None, description="종국결과")
  parties_summary: str | None = Field(default=None, description="원고/피고 요약")
  basic_info: dict[str, str] = Field(
    default_factory=dict, description="기본정보 라벨→값 전체"
  )
  hearings: list[dict] = Field(default_factory=list, description="기일내역")
  submissions: list[dict] = Field(
    default_factory=list, description="제출서류 접수내역(진행)"
  )
  parties: list[dict] = Field(default_factory=list, description="당사자내역")
  agents: list[dict] = Field(default_factory=list, description="대리인내역")


class CaptchaChallenge(BaseModel):
  """CAPTCHA 1단계 응답 — 사용자에게 보여줄 이미지와 세션 토큰."""

  # 'session_id' 라는 이름은 원격 Cowork 중계가 툴 인자에서 제거해 버리므로 쓰지 않는다.
  challenge_id: str = Field(description="case_search_submit 호출 시 그대로 전달")
  captcha_image_path: str = Field(description="저장된 CAPTCHA 이미지 파일 경로")
  message: str = Field(description="사용자 안내 문구")
