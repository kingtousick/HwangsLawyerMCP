"""사건번호 파서 단위 테스트.

두 사이트의 파서는 받아들이는 형식이 다르다. 나의 사건검색은 2자리 연도를
허용해 4자리로 보정하지만, 경매 검색은 4자리 연도만 받는다. 이 차이가
의도된 것임을 고정해 둔다.
"""

import pytest

from lawyer_mcp import courtauction, scourt


class TestScourtParseCaseNo:
  """나의 사건검색(ssgo) — 2자리 연도 보정과 사건구분 분리."""

  @pytest.mark.parametrize(
    "case_no, expected",
    [
      ("25자10000", ("2025", "자", "10000")),
      ("2025자10000", ("2025", "자", "10000")),
      ("2025가단5934", ("2025", "가단", "5934")),
      ("2024가단12345", ("2024", "가단", "12345")),
      ("2024나1234", ("2024", "나", "1234")),
      (" 2025 가단 5934 ", ("2025", "가단", "5934")),  # 공백 허용
    ],
  )
  def test_parses(self, case_no, expected):
    assert scourt.parse_case_no(case_no) == expected

  @pytest.mark.parametrize(
    "case_no, expected_year",
    [
      ("49가소123", "2049"),  # 50 미만 -> 2000년대
      ("50가소123", "1950"),  # 50 이상 -> 1900년대
      ("99가소123", "1999"),
      ("00가소123", "2000"),
    ],
  )
  def test_two_digit_year_normalization(self, case_no, expected_year):
    assert scourt.parse_case_no(case_no)[0] == expected_year

  @pytest.mark.parametrize("bad", ["", "가단", "12345", "abc123", "2025가단"])
  def test_rejects_malformed(self, bad):
    with pytest.raises(ValueError, match="사건번호 형식"):
      scourt.parse_case_no(bad)


class TestCourtauctionParseCaseNo:
  """법원경매 — 4자리 연도만 받는다."""

  @pytest.mark.parametrize(
    "case_no, expected",
    [
      ("2024타경12345", ("2024", "타경", "12345")),
      ("2024타경 12345", ("2024", "타경", "12345")),
      ("2025타경602", ("2025", "타경", "602")),
    ],
  )
  def test_parses(self, case_no, expected):
    assert courtauction.parse_case_no(case_no) == expected

  @pytest.mark.parametrize("bad", ["", "타경602", "25타경602", "2024타경"])
  def test_rejects_malformed(self, bad):
    """2자리 연도('25타경602')는 경매 쪽에서 지원하지 않는다."""
    with pytest.raises(ValueError, match="사건번호 형식"):
      courtauction.parse_case_no(bad)
