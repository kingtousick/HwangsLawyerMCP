"""법원경매정보(courtauction.go.kr) 검색 클라이언트.

WebSquare(w2xPath) 프레임워크라 DOM 셀렉터가 내부 ID 기반이며, 사이트가
개편되면 셀렉터를 다시 맞춰야 한다. 셀렉터는 id 의 suffix 로 매칭한다.

두 가지 검색 경로를 제공한다(라이브 검증 2026-06):
  1) 경매사건검색(PGJ159M00) — 법원+사건번호로 '사건 전체'를 조회한다.
     날짜 필터가 없어 미종국·취하·종국 사건까지 바로 나온다. → case_search()
  2) 물건상세검색(PGJ151F00) — '진행 중 매각물건'을 조회한다. 매각기일이
     설정된 부동산만 나오며 기일내역이 상세하다. → search_by_case()/item_detail()
사건번호로 사건을 찾는 일반적 용도는 (1) 경매사건검색이 맞다.
"""

from __future__ import annotations

import re

from playwright.async_api import Page

from .browser import manager
from .models import AuctionCase, AuctionItem, AuctionItemDetail

# 물건상세검색 페이지 (진행 중 매각물건)
SEARCH_URL = (
  "https://www.courtauction.go.kr/pgj/index.on"
  "?w2xPath=/pgj/ui/pgj100/PGJ151F00.xml"
)

# 경매사건검색 페이지 (사건번호로 사건 전체 조회)
CASE_SEARCH_URL = (
  "https://www.courtauction.go.kr/pgj/index.on"
  "?w2xPath=/pgj/ui/pgj100/PGJ159M00.xml"
)

# --- 라이브 검증 완료 셀렉터 (suffix 매칭, 2026-06) -----------------------
# 물건상세검색(PGJ151F00) 폼. WebSquare prefix: mf_wfm_mainFrame_
_SEL_COURT_SELECT = "select[id$='_sbx_rletCortOfc']"   # 법원 선택(값=법원명)
_SEL_CASE_YEAR = "select[id$='_sbx_rletCsYear']"       # 사건 연도 (select)
_SEL_CASE_NO = "input[id$='_ibx_rletCsNo']"            # 사건번호 일련번호
_SEL_SEARCH_BTN = "input[id$='_btn_gdsDtlSrch']"       # 부동산 물건상세 검색 버튼

# 경매사건검색(PGJ159M00) 폼 셀렉터
_SEL_CS_COURT = "select[id$='_sbx_auctnCsSrchCortOfc']"  # 법원(값=법원명)
_SEL_CS_YEAR = "select[id$='_sbx_auctnCsSrchCsYear']"    # 연도 (select)
_SEL_CS_NO = "input[id$='_ibx_auctnCsSrchCsNo']"         # 사건 일련번호
_SEL_CS_BTN = "input[id$='_btn_auctnCsSrchBtn']"         # 검색 버튼
# -------------------------------------------------------------------------

# 사건번호 형식: "2024타경12345" 또는 "2024타경 12345"
_CASE_RE = re.compile(r"(?P<year>\d{4})\s*(?P<type>[가-힣]+)\s*(?P<seq>\d+)")


def parse_case_no(case_no: str) -> tuple[str, str, str]:
  """'2024타경12345' -> ('2024', '타경', '12345')."""
  m = _CASE_RE.search(case_no.strip())
  if not m:
    raise ValueError(
      f"사건번호 형식을 인식할 수 없습니다: {case_no!r} "
      "(예: '2024타경12345')"
    )
  return m.group("year"), m.group("type"), m.group("seq")


async def _fill_and_search(page: Page, case_no: str, court: str | None) -> None:
  """검색 폼을 채우고 조회 버튼을 누른다.

  물건상세검색은 사건구분이 '타경'(부동산)으로 고정이라, 연도+일련번호만
  입력한다. 연도는 select, 사건번호 일련번호는 text input 이다.
  """
  year, _type, seq = parse_case_no(case_no)

  # networkidle 은 WebSquare 정부 사이트의 지속적 네트워크 활동 때문에 도달하지
  # 못해 타임아웃의 원인이 된다. domcontentloaded 로 빠르게 받고, 폼 셀렉터
  # 대기(_SEL_CASE_NO)로 렌더링 완료를 보장한다.
  await page.goto(SEARCH_URL, wait_until="domcontentloaded", timeout=30000)
  await page.wait_for_selector(_SEL_CASE_NO, timeout=20000)

  if court:
    # 법원명이 주어지면 select 에서 선택(값=라벨=법원명). 값 우선, 실패 시 라벨.
    try:
      await page.select_option(_SEL_COURT_SELECT, value=court)
    except Exception:
      try:
        await page.select_option(_SEL_COURT_SELECT, label=court)
      except Exception:
        pass  # 옵션 불일치 시 법원 미지정으로 진행

  # 연도 드롭다운에 없는 값이면 30초 타임아웃 대신 즉시 명확한 에러를 낸다.
  try:
    await page.select_option(_SEL_CASE_YEAR, value=year, timeout=5000)
  except Exception:
    years = await page.locator(f"{_SEL_CASE_YEAR} option").all_inner_texts()
    raise ValueError(
      f"조회할 수 없는 연도입니다: {year} "
      f"(경매 검색 가능 연도 범위: {years[-1] if years else '?'}~"
      f"{years[0] if years else '?'})"
    )
  await page.fill(_SEL_CASE_NO, seq)
  await page.click(_SEL_SEARCH_BTN)
  # networkidle 대기는 정부 사이트에서 도달하지 못하고 예외/지연만 낸다.
  # 결과 그리드는 AJAX 로 채워지므로 데이터 셀(td)이 생길 때까지 기다린다.
  # 조회결과 0건이면 td 가 없어 타임아웃 — 이 경우는 무시하고 빈 목록으로 둔다.
  try:
    await page.wait_for_selector(
      f"table[id$='{_RESULT_GRID_SUFFIX}'] td", timeout=10000
    )
  except Exception:
    pass


def _cell(text: str | None) -> str | None:
  if text is None:
    return None
  t = text.strip()
  return t or None


# 결과 그리드는 '물건 1건 = tr 2줄' 구조다(라이브 검증 2026-06).
#   1줄(td 8): [0]체크박스 [1]사건번호 [2]물건번호 [3]소재지 [4]비고
#              [5]사진(빈칸) [6]감정평가액 [7]담당계·매각기일
#   2줄(td 3): [0]용도 [1]최저매각가격 [2]진행상태
_RESULT_GRID_SUFFIX = "_grd_gdsDtlSrchResult_body_table"


async def _extract_items(page: Page) -> list[dict]:
  """결과 그리드를 tr 2줄 단위로 묶어 물건별 dict 리스트로 반환한다."""
  return await page.evaluate(
    """(suffix) => {
      const txt = (el) => (el.innerText || '').trim().replace(/\\s+/g, ' ');
      const tb = [...document.querySelectorAll('table')]
        .find(t => t.id && t.id.endsWith(suffix));
      if (!tb) return [];
      const trs = [...tb.querySelectorAll('tr')];
      const items = [];
      for (let i = 0; i < trs.length; i++) {
        const c = [...trs[i].querySelectorAll('td')].map(txt);
        if (c.length < 8) continue;            // 헤더(th)·잡행 스킵, 1줄만 처리
        let s = [];
        if (i + 1 < trs.length) {
          const nxt = [...trs[i + 1].querySelectorAll('td')].map(txt);
          if (nxt.length === 3) { s = nxt; i++; }  // 2줄을 묶고 인덱스 전진
        }
        items.push({
          case_no_raw: c[1] || null,
          item_no: c[2] || null,
          address: c[3] || null,
          note: c[4] || null,
          appraisal_value: c[6] || null,
          bid_date: c[7] || null,         // 담당계 + 매각기일
          item_type: s[0] || null,        // 용도
          min_bid_value: s[1] || null,    // 최저매각가격
          status: s[2] || null,           // 진행상태(유찰 N회 등)
        });
      }
      return items;
    }""",
    _RESULT_GRID_SUFFIX,
  )


async def search_by_case(case_no: str, court: str | None = None) -> list[AuctionItem]:
  """사건번호로 경매 물건 목록을 조회한다."""
  async with manager.page() as page:
    await _fill_and_search(page, case_no, court)

    raw = await _extract_items(page)
    items: list[AuctionItem] = []
    for it in raw:
      items.append(
        AuctionItem(
          case_no=case_no,
          item_no=_cell(it.get("item_no")),
          court=court,
          item_type=_cell(it.get("item_type")),
          address=_cell(it.get("address")),
          appraisal_value=_cell(it.get("appraisal_value")),
          min_bid_value=_cell(it.get("min_bid_value")),
          bid_date=_cell(it.get("bid_date")),
          status=_cell(it.get("status")),
        )
      )
    return items


# 상세 화면 기일내역 그리드(안정 id suffix, 라이브 검증 2026-06)
_DETAIL_HEARING_SUFFIX = "_grd_dxdyDtsLst_body_table"


async def _extract_detail(page: Page) -> dict:
  """물건상세 화면에서 기본정보·사건정보·기일내역을 구조화해 추출한다.

  기본정보/사건정보 테이블은 id 가 가변(uuid)이라, 포함된 라벨 키워드로 찾고
  라벨/값 쌍으로 파싱한다. 기일내역은 안정 id suffix 로 찾는다.
  """
  return await page.evaluate(
    """(hearingSuffix) => {
      const txt = (el) => (el.innerText || '').trim().replace(/\\s+/g, ' ');

      // 필수 키워드를 모두 포함한 테이블을 라벨/값 쌍으로 파싱
      const pairTable = (keywords) => {
        const tb = [...document.querySelectorAll('table')].find(t => {
          const s = txt(t);
          return keywords.every(k => s.includes(k));
        });
        const o = {};
        if (!tb) return o;
        for (const tr of tb.querySelectorAll('tr')) {
          const cells = [...tr.querySelectorAll('th,td')].map(txt);
          for (let i = 0; i + 1 < cells.length; i += 2) {
            if (cells[i]) o[cells[i]] = cells[i + 1];
          }
        }
        return o;
      };

      const basic = pairTable(['물건종류', '감정평가액', '입찰방법']);
      const caseInfo = pairTable(['사건접수', '경매개시일', '배당요구종기']);

      // 기일내역 그리드: 첫 행 헤더 + 나머지 데이터
      const tb = [...document.querySelectorAll('table')]
        .find(t => t.id && t.id.endsWith(hearingSuffix));
      let hearings = [];
      if (tb) {
        const rows = [...tb.querySelectorAll('tr')]
          .map(tr => [...tr.querySelectorAll('th,td')].map(txt))
          .filter(r => r.some(x => x));
        if (rows.length >= 2) {
          const h = rows[0];
          hearings = rows.slice(1).map(r => {
            const o = {};
            h.forEach((k, i) => { o[k || ('col' + i)] = r[i] ?? ''; });
            return o;
          });
        }
      }
      return { basic, caseInfo, hearings };
    }""",
    _DETAIL_HEARING_SUFFIX,
  )


def _find_key(d: dict, *subs: str) -> str | None:
  """키에 부분문자열이 포함된 첫 값을 반환(라벨에 괄호 주석이 붙는 경우 대비)."""
  for k, v in d.items():
    if all(s in k for s in subs):
      return _cell(v)
  return None


async def item_detail(case_no: str, item_no: str | None = None,
                      court: str | None = None) -> AuctionItemDetail | None:
  """특정 물건의 상세 정보(기일 내역 포함)를 조회한다.

  물건상세는 결과 그리드에서 해당 물건의 소재지 링크를 클릭하면 같은 페이지에
  인라인으로 렌더된다(WebSquare SPA). item_no 미지정 시 첫 물건을 연다.
  """
  async with manager.page() as page:
    await _fill_and_search(page, case_no, court)

    raw = await _extract_items(page)
    if not raw:
      return None

    # item_no 로 대상 물건의 인덱스를 찾는다(미지정 시 0). 행당 소재지 링크 1개라
    # 링크 순서가 물건 순서와 일치한다.
    target = 0
    chosen = raw[0]
    if item_no:
      for idx, it in enumerate(raw):
        if str(it.get("item_no")) == str(item_no):
          target, chosen = idx, it
          break

    tb_sel = f"table[id$='{_RESULT_GRID_SUFFIX}']"
    anchors = page.locator(f"{tb_sel} tbody tr td a")
    if await anchors.count() <= target:
      return None
    await anchors.nth(target).click()
    # 상세 기일내역 그리드가 렌더될 때까지 대기
    try:
      await page.wait_for_selector(
        f"table[id$='{_DETAIL_HEARING_SUFFIX}']", timeout=15000
      )
    except Exception:
      pass
    # 상세 그리드 대기(위)가 렌더 완료를 보장한다. networkidle 은 정부 사이트에서
    # 도달하지 못하므로 추가 대기를 두지 않는다.

    d = await _extract_detail(page)
    basic = d["basic"]

    detail = AuctionItemDetail(
      case_no=case_no,
      item_no=_cell(chosen.get("item_no")),
      court=court,
      item_type=_find_key(basic, "물건종류") or _cell(chosen.get("item_type")),
      address=_cell(chosen.get("address")),
      appraisal_value=_find_key(basic, "감정평가액")
      or _cell(chosen.get("appraisal_value")),
      min_bid_value=_find_key(basic, "최저매각가격")
      or _cell(chosen.get("min_bid_value")),
      bid_date=_find_key(basic, "매각기일") or _cell(chosen.get("bid_date")),
      status=_cell(chosen.get("status")),
      notes=_find_key(basic, "물건비고"),
    )
    detail.bid_history = d["hearings"]
    # 기일결과에 '유찰'이 포함된 기일 수로 유찰횟수 산정
    detail.failed_count = sum(
      1 for h in detail.bid_history
      if any("유찰" in (v or "") for v in h.values())
    )
    return detail


# ===== 경매사건검색(PGJ159M00) — 사건번호로 사건 전체 조회 ==================

async def _extract_case(page: Page) -> dict:
  """경매사건검색 결과에서 기본정보·물건목록·당사자·목록을 추출한다."""
  return await page.evaluate(
    """() => {
      const txt = (el) => (el.innerText || '').trim().replace(/\\s+/g, ' ');

      // th(라벨)+td(값) 쌍 파싱 (id suffix 로 테이블 지정)
      const pairBySuffix = (suffix) => {
        const tb = [...document.querySelectorAll('table')]
          .find(t => t.id && t.id.endsWith(suffix));
        const o = {};
        if (!tb) return o;
        for (const tr of tb.querySelectorAll('tr')) {
          const cs = [...tr.querySelectorAll('th,td')];
          for (let i = 0; i + 1 < cs.length; i++) {
            if (cs[i].tagName === 'TH' && cs[i + 1].tagName === 'TD') {
              const k = txt(cs[i]);
              if (k && !(k in o)) o[k] = txt(cs[i + 1]);  // 첫 등장만
            }
          }
        }
        return o;
      };

      const basic = pairBySuffix('_grp_csNoBasDt');

      // 물건목록: gen_gdsDts_N_grp_gdsDtsTbl 블록마다 라벨/값 묶음
      const items = [];
      const seen = new Set();
      for (const tb of document.querySelectorAll(
          "table[id*='gen_gdsDts'][id$='_grp_gdsDtsTbl']")) {
        if (seen.has(tb.id)) continue; seen.add(tb.id);
        const o = {};
        for (const tr of tb.querySelectorAll('tr')) {
          const cs = [...tr.querySelectorAll('th,td')];
          for (let i = 0; i + 1 < cs.length; i++) {
            if (cs[i].tagName === 'TH' && cs[i + 1].tagName === 'TD') {
              const k = txt(cs[i]), v = txt(cs[i + 1]);
              if (k && !(k in o)) o[k] = v;
            }
          }
        }
        if (Object.keys(o).length) items.push(o);
      }

      // 당사자: grd_ttt, 한 행에 (구분,이름) 최대 2쌍
      const parties = [];
      const pt = [...document.querySelectorAll('table')]
        .find(t => t.id && t.id.endsWith('_grd_ttt_body_table'));
      if (pt) {
        for (const tr of pt.querySelectorAll('tr')) {
          const r = [...tr.querySelectorAll('th,td')].map(txt);
          if (r[0] === '당사자구분') continue;            // 헤더 스킵
          if (r[0] && r[1]) parties.push({ 구분: r[0], 이름: r[1] });
          if (r[2] && r[3]) parties.push({ 구분: r[2], 이름: r[3] });
        }
      }

      // 목록(소재지): 헤더 키워드로 식별
      const listings = [];
      const lt = [...document.querySelectorAll('table')].find(t => {
        const s = txt(t);
        return s.includes('목록번호') && s.includes('소재지')
          && s.includes('등기기록');
      });
      if (lt) {
        const rows = [...lt.querySelectorAll('tr')]
          .map(tr => [...tr.querySelectorAll('th,td')].map(txt))
          .filter(r => r.some(x => x));
        if (rows.length >= 2) {
          const h = rows[0];
          for (const r of rows.slice(1)) {
            if (!r[0]) continue;
            const o = {};
            h.forEach((k, i) => { o[k || ('col' + i)] = r[i] ?? ''; });
            listings.push(o);
          }
        }
      }

      return { basic, items, parties, listings };
    }"""
  )


async def case_search(case_no: str, court: str) -> AuctionCase | None:
  """경매사건검색으로 사건번호의 사건 전체 정보를 조회한다.

  Args:
    case_no: 사건번호 (예: '2025타경602').
    court: 법원명. 경매사건검색 드롭다운 값과 일치해야 한다(지원은 짧은 이름,
      예: '순천지원'). 값 우선, 실패 시 라벨로 매칭한다.

  Returns:
    AuctionCase. 사건을 찾지 못하면 None.
  """
  year, _type, seq = parse_case_no(case_no)

  async with manager.page() as page:
    # 조회 실패 안내(alert) 캡처
    dialog_messages: list[str] = []

    async def _on_dialog(dialog):
      dialog_messages.append(dialog.message)
      try:
        await dialog.accept()
      except Exception:
        pass

    page.on("dialog", _on_dialog)

    # networkidle 은 WebSquare 정부 사이트에서 도달하지 못해 타임아웃의 원인이
    # 된다. domcontentloaded 로 빠르게 받고, 폼 셀렉터 대기(_SEL_CS_NO)로
    # 렌더링 완료를 보장한다.
    await page.goto(CASE_SEARCH_URL, wait_until="domcontentloaded", timeout=30000)
    await page.wait_for_selector(_SEL_CS_NO, timeout=20000)

    try:
      await page.select_option(_SEL_CS_COURT, value=court, timeout=5000)
    except Exception:
      try:
        await page.select_option(_SEL_CS_COURT, label=court, timeout=5000)
      except Exception:
        raise ValueError(f"경매사건검색에서 법원을 찾을 수 없습니다: {court!r}")

    try:
      await page.select_option(_SEL_CS_YEAR, value=year, timeout=5000)
    except Exception:
      years = await page.locator(f"{_SEL_CS_YEAR} option").all_inner_texts()
      raise ValueError(
        f"조회할 수 없는 연도입니다: {year} "
        f"(가능 범위: {years[-1] if years else '?'}~{years[0] if years else '?'})"
      )

    await page.fill(_SEL_CS_NO, seq)
    await page.click(_SEL_CS_BTN)
    # networkidle 대기는 정부 사이트에서 도달하지 못하고 예외/지연만 낸다.
    # 기본정보는 AJAX 로 채워진다. 빈 템플릿에도 '사건명' 라벨은 있으므로,
    # 사건번호 값에 '타경'이 들어올 때까지(=실데이터 도착) 기다린다.
    # 없는 사건이면 템플릿('-전자')이 유지되어 타임아웃 → 무결과로 처리.
    try:
      await page.wait_for_function(
        "() => { const t=[...document.querySelectorAll('table')]"
        ".find(x=>x.id&&x.id.endsWith('_grp_csNoBasDt'));"
        " return t && t.innerText.includes('타경'); }",
        timeout=12000,
      )
    except Exception:
      pass

    d = await _extract_case(page)
    basic = d["basic"]

    # 사이트는 빈 값을 '-' 로 표기한다 → 플레이스홀더를 None 으로 정규화
    def clean(v: str | None) -> str | None:
      v = _cell(v)
      return None if v in (None, "-", "-원", "-전자") else v

    # 조회 실패 판정: 경고창이 떴거나 사건명/사건번호가 실제로 없음
    name = clean(basic.get("사건명"))
    if dialog_messages and not name:
      msg = " / ".join(m.strip() for m in dialog_messages if m and m.strip())
      raise ValueError(f"조회 실패: {msg or '사건을 찾을 수 없습니다.'}")
    if not name and not d["parties"] and not d["items"]:
      return None

    dept = (basic.get("담당계") or "").split(" 전화")[0].strip()
    dept = dept if dept and not dept.startswith("(") else None

    # 핵심 당사자(채권자/채무자) 요약을 만든다.
    def first_party(*keywords: str) -> str | None:
      for p in d["parties"]:
        gubun = p.get("구분", "")
        if any(k in gubun for k in keywords):
          return f"{gubun} {p.get('이름', '')}".strip()
      return None

    summary_parts = [
      x for x in (first_party("채권자"), first_party("채무자", "소유자")) if x
    ]
    parties_summary = " / ".join(summary_parts) or None

    return AuctionCase(
      court=court,
      case_no=case_no,
      case_name=name,
      filed_date=clean(basic.get("접수일자")),
      start_decision_date=clean(basic.get("개시결정일자")),
      department=dept,
      claim_amount=clean(basic.get("청구금액")),
      final_result=clean(basic.get("종국결과")),
      final_date=clean(basic.get("종국일자")),
      parties_summary=parties_summary,
      basic_info=basic,
      items=d["items"],
      listings=d["listings"],
      parties=d["parties"],
    )
