# 법원 경매/사건검색 MCP 서버 (lawyer-mcp)

법원 사이트에서 **사건번호로 검색**하는 MCP 서버입니다.
Playwright(헤드리스 브라우저)로 WebSquare 기반 정부 사이트를 조작합니다.

## 제공 툴

| 툴 | 대상 사이트 | 설명 |
|---|---|---|
| `auction_case_search` | 경매사건검색 | 법원+사건번호로 **사건 전체** 조회(미종국/취하 포함) |
| `auction_search_by_case` | 물건상세검색 | 사건번호로 **진행 중 매각물건** 목록 검색 |
| `auction_item_detail` | 물건상세검색 | 진행 물건 상세(감정가/최저가/기일 내역) |
| `case_search_captcha` | 나의 사건검색 | **1단계** — CAPTCHA 이미지 반환 |
| `case_search_submit` | 나의 사건검색 | **2단계** — CAPTCHA 입력 후 조회 |

> **경매 사건번호 조회는 `auction_case_search` 를 우선 사용하세요.**
> 날짜 필터가 없어 진행 중·미종국·취하·종국 사건까지 바로 나오며, 사건
> 기본정보·물건목록·당사자·목록(소재지)을 함께 돌려줍니다.
> `auction_search_by_case`/`auction_item_detail` 는 매각기일이 잡힌 '진행 중
> 매각물건'만 다루므로, 진행물건이 없는 사건은 빈 결과가 됩니다.
> (지원 법원명은 짧은 이름 — 예: `광주지방법원 순천지원` → `순천지원`)

> **나의 사건검색은 CAPTCHA(자동입력 방지문자) 때문에 반자동입니다.**
> 1단계에서 받은 이미지를 사람이 읽고, 2단계에 그 값을 넣어야 조회됩니다.
> CAPTCHA 자동 우회는 시도하지 않습니다.

> **조회 실패 처리:** 당사자명 불일치·사건 없음·CAPTCHA 오류 시 법원 사이트가
> 띄우는 경고창 문구(예: `사건이 존재하지 않습니다.`)를 그대로 에러로 반환합니다.
> 경고창 없이 검색 폼으로 되돌아온 경우도 `조회 결과를 찾을 수 없습니다` 에러로 처리합니다.

## 설치

### 1) 저장소 클론
```powershell
git clone https://github.com/kingtousick/HwangsLawyerMCP.git
cd HwangsLawyerMCP
```

### 2) Python 환경 준비
Python 3.10+ 이 필요합니다. 아래 중 하나로 의존성과 브라우저(Chromium)를 설치하세요.

#### 방법 A — uv (권장)
```powershell
# uv 가 없으면 먼저 설치
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
# (새 터미널을 연 뒤) 클론한 폴더에서:
uv sync
uv run playwright install chromium
```

#### 방법 B — python.org 설치본
1. https://www.python.org/downloads/ 에서 3.12 설치 (설치 시 *Add to PATH* 체크)
2. 클론한 폴더에서:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -e .
   playwright install chromium
   ```

## 실행 / 동작 확인

```powershell
# uv 사용 시
uv run lawyer-mcp
# venv 사용 시
lawyer-mcp
```
서버는 stdio MCP 트랜스포트로 동작하므로 직접 실행하면 입력 대기 상태가 됩니다(정상).

### MCP 인스펙터로 테스트
```powershell
uv run mcp dev src/lawyer_mcp/server.py
```

## Claude Code 에 등록

아래 설정에서 `<REPO_DIR>` 은 **클론한 폴더의 절대경로**로 바꿔주세요.
(예: `C:\Users\alice\HwangsLawyerMCP`, `/home/alice/HwangsLawyerMCP`)

`%USERPROFILE%\.claude.json` 또는 프로젝트 `.mcp.json` 의 `mcpServers` 에 추가:

```json
{
  "mcpServers": {
    "lawyer": {
      "command": "uv",
      "args": ["--directory", "<REPO_DIR>", "run", "lawyer-mcp"]
    }
  }
}
```
> JSON 에 Windows 경로를 넣을 때는 역슬래시를 두 번(`C:\\Users\\alice\\...`) 쓰거나
> 슬래시(`C:/Users/alice/...`)를 사용하세요.

또는 CLI 로 — 클론한 폴더 안에서 실행하면 절대경로를 직접 쓰지 않아도 됩니다:
```powershell
# PowerShell (클론한 폴더에서)
claude mcp add lawyer -- uv --directory $PWD run lawyer-mcp
```
```bash
# bash/zsh (클론한 폴더에서)
claude mcp add lawyer -- uv --directory "$PWD" run lawyer-mcp
```

## 환경 변수

| 변수 | 기본값 | 설명 |
|---|---|---|
| `LAWYER_MCP_HEADLESS` | `1` | `0` 으로 두면 브라우저 창을 띄움(디버깅/셀렉터 검증용) |
| `LAWYER_MCP_CAPTCHA_DIR` | `<REPO_DIR>/.captcha` | CAPTCHA 이미지 저장 경로 |
| `LAWYER_MCP_SESSION_TTL` | `600` | 나의 사건검색 세션 유효시간(초) |

> `LAWYER_MCP_CAPTCHA_DIR` 은 **MCP 클라이언트가 읽을 수 있는 폴더**로 지정하면
> 클라이언트 쪽 모델이 이미지를 직접 읽어 CAPTCHA 를 입력할 수 있습니다.

> **CAPTCHA 이미지는 자동 정리됩니다.** `case_search_submit` 이 끝나면 해당
> 이미지를 지우고, 조회를 중단해 버려진 세션은 TTL 이 지난 뒤 다음 호출 때
> 컨텍스트·이미지가 함께 정리됩니다. 세션 없이 남은 `captcha_*.png` 도 1시간이
> 지나면 걷어냅니다(그 폴더의 다른 파일은 건드리지 않습니다).

### 검증/탐침 스크립트 전용 (`scripts/`)

| 변수 | 기본값 | 설명 |
|---|---|---|
| `LAWYER_MCP_OUT_DIR` | 저장소 루트 | 스크린샷·DOM 덤프 등 산출물 저장 경로 |
| `LAWYER_MCP_TEST_COURT` | `○○시법원` | 검증에 쓸 법원명 |
| `LAWYER_MCP_TEST_CASE_NO` | `25자10000` | 검증에 쓸 사건번호 |
| `LAWYER_MCP_TEST_PARTY` | `홍길동` | 검증에 쓸 당사자명 |

> `scripts/` 의 검증 스크립트는 **실제 사건**으로 조회해야 의미가 있습니다.
> 실사건 정보는 저장소에 커밋하지 말고 위 환경변수로 주입하세요.
>
> ```powershell
> $env:LAWYER_MCP_TEST_COURT = "○○지방법원"
> $env:LAWYER_MCP_TEST_CASE_NO = "24가단12345"
> $env:LAWYER_MCP_TEST_PARTY  = "홍길동"
> uv run python scripts/verify_full.py
> ```

> **법원명 표기 주의**(나의 사건검색): 시·군법원은 단축명(`여수시법원`),
> 지방법원 본원·지원은 풀네임(`광주지방법원 순천지원`)이어야 select 옵션과
> 매칭됩니다. 경매 사이트는 지원을 단축명(`순천지원`)으로 받으니 서로 다릅니다.

### 출력 인코딩

`scripts/_common.py` 가 임포트 시점에 stdout/stderr 를 **UTF-8 로 재설정**합니다.
Windows 기본 콘솔 인코딩(cp949)에서 한글이 깨지거나, 결과를 파일로 리다이렉트했을 때
cp949 로 기록되는 문제를 막기 위한 것으로, `PYTHONIOENCODING` 을 따로 지정하지 않아도 됩니다.

```powershell
uv run python scripts/verify_full.py > result.txt   # result.txt 는 UTF-8
```

## 셀렉터 검증 상태

| 모듈 | 대상 | 폼 입력 | 결과 파싱 |
|---|---|---|---|
| `scourt.py` | `ssgo.scourt.go.kr` | ✅ 검증 완료(2026-06) | ✅ 검증 완료(2026-06, 실사건 조회) |
| `courtauction.py` | `courtauction.go.kr` | ✅ 검증 완료(2026-06) | ✅ 검증 완료(2026-06, 실사건 조회) |

> `scourt.py` 는 실제 사건으로 **폼 입력 → CAPTCHA → 결과 파싱**까지 전 구간 검증을 마쳤습니다.
> (기본정보·기일내역·제출서류·당사자·대리인 그리드 모두 정상 추출)
> 재검증: `scripts/verify_full.py`, `scripts/probe_scourt.py`
>
> `courtauction.py` 도 실제 사건으로 전 구간 검증을 마쳤습니다.
> - **경매사건검색**(`case_search`): 법원+사건번호 → 기본정보·물건목록·당사자·목록
>   추출 검증(예: `2025타경602` 순천지원, 당사자 16명). 무결과는 `None`.
> - **물건상세검색**(`search_by_case`/`item_detail`): 결과 그리드 '물건 1건 = 행
>   2줄' 구조, 물건상세는 소재지 링크 클릭 시 같은 페이지 인라인 렌더, 기일내역
>   파싱까지 검증. 무결과·범위 밖 연도 등 예외도 명확한 에러/빈 결과로 처리.
> 재검증: `scripts/verify_case_search.py`, `scripts/verify_auction.py`,
> `scripts/probe_case_*.py`, `scripts/probe_auction*.py`

정부 사이트는 WebSquare 내부 ID 기반이라, 실제 페이지를 열어 element id 를 확인해야 합니다.

```powershell
# 브라우저를 띄운 채 실제 DOM 확인
$env:LAWYER_MCP_HEADLESS = "0"
uv run mcp dev src/lawyer_mcp/server.py
```
개발자도구(F12)로 입력칸/버튼/결과 테이블의 실제 id 를 확인한 뒤
각 파일 상단의 `_SEL_*` 상수를 교체하세요. 사이트 개편 시에도 이 부분만 손보면 됩니다.

## 주의 / 한계

- 법원 사이트의 **이용약관과 robots 정책**을 준수하고, 과도한 요청을 피하세요.
- 전자소송(ecfs)의 사건 상세는 **공동인증서 로그인**이 필요해 이 서버 범위에 넣지 않았습니다.
- 사이트 구조 변경 시 셀렉터 업데이트가 필요합니다.
