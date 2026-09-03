# 다른 PC에서 세팅 가이드

이 시스템은 4개 요소로 구성됩니다. 새 PC에서는 아래 순서대로 옮기거나 다시 만들면 됩니다.

1. **lawyer-mcp** (법원 조회 MCP 서버, 패치 적용본) — Git으로 이전
2. **Claude Desktop 커넥터 등록** — 새 PC에서 재등록 (경로 수정)
3. **Cowork 작업폴더 + 추적표 파일** — 새 PC에서 연결 (경로 수정)
4. **주간 스케줄 작업** — 새 PC에서 재생성 (경로 수정)

> 스케줄 작업과 커넥터 등록은 **PC마다 로컬에 저장**되어 자동으로 따라오지 않습니다. 새 PC에서 다시 만들어야 합니다.

---

## 0. 사전 준비 (새 PC)

- Windows + **Claude Desktop**(Cowork 사용 가능 버전)
- **Python 3.12+**
- **uv** (권장): PowerShell에서
  ```powershell
  powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
  ```
- **git**

---

## 1. (현재 PC에서) 패치를 GitHub에 올리기

현재 PC의 PowerShell에서 lawyer-mcp 폴더로 이동해 **scourt.py만** 커밋·푸시합니다.

```powershell
cd <lawyer-mcp 소스 폴더>
git add src/lawyer_mcp/scourt.py
git commit -m "fix(scourt): CAPTCHA 저장경로 기본값을 repo/.captcha로, goto를 domcontentloaded로 (system32 권한오류·타임아웃 해결)"
git push origin main
```

> Windows git에서는 보통 `scourt.py` 한 파일만 변경으로 잡힙니다. 혹시 다른 파일들이 함께 떠도(줄바꿈 CRLF 차이) 위처럼 `scourt.py`만 `git add` 하면 됩니다.
> 푸시할 때 GitHub 로그인(또는 토큰)이 필요합니다. 저장소: `https://github.com/kingtousick/HwangsLawyerMCP.git`

패치 내용 자체는 이 문서 맨 끝 **부록 A**에 있습니다. (Git을 안 쓰고 직접 고치고 싶을 때 사용)

---

## 2. (새 PC) 클론 & 설치

```powershell
cd C:\Users\<사용자명>            # 원하는 상위 폴더로
git clone https://github.com/kingtousick/HwangsLawyerMCP.git
cd HwangsLawyerMCP
uv sync
uv run playwright install chromium
```

설치 확인(선택): `uv run lawyer-mcp` → 입력 대기 상태가 되면 정상(Ctrl+C로 종료).

---

## 3. (새 PC) Claude Desktop에 커넥터 등록

현재 PC에서 등록했던 것과 **같은 방식**으로 lawyer-mcp를 등록합니다(설정 → 커넥터/확장 → 로컬 MCP 추가). 명령/경로/환경변수는 아래로:

```json
{
  "command": "uv",
  "args": ["--directory", "C:\\Users\\<사용자명>\\HwangsLawyerMCP", "run", "lawyer-mcp"],
  "env": {
    "LAWYER_MCP_CAPTCHA_DIR": "C:\\Users\\<사용자명>\\Claude\\Projects\\사건조회\\_captcha"
  }
}
```

> **`LAWYER_MCP_CAPTCHA_DIR` 권장 설정 이유**: 캡차 이미지를 **Cowork 작업폴더 안**(`_captcha`)에 저장하면, Cowork의 Claude가 그 이미지를 읽어 캡차를 자동으로 풀 수 있습니다. (지정하지 않으면 기본값은 `소스폴더\.captcha`이며, 그 경우 그 폴더를 Cowork에 연결해야 읽힙니다.)

등록 후 **Claude Desktop을 재시작**해야 적용됩니다.

---

## 4. (새 PC) Cowork 작업폴더 연결 + 추적표 복사

1. 작업폴더 생성: 예) `C:\Users\<사용자명>\Claude\Projects\사건조회`
2. 그 안에 `_captcha` 폴더 생성(3번 env와 일치). 없으면 첫 실행 때 자동 생성됩니다.
3. 현재 PC의 **사건추적표 `.xlsx`** 파일을 이 폴더로 복사. (복사 안 하면 첫 주간 실행 때 새로 만들어집니다.)
4. Cowork에서 이 작업폴더를 **연결**(폴더 선택 승인).

---

## 5. (새 PC) 주간 스케줄 작업 재생성

가장 쉬운 방법 — Cowork 채팅에 이렇게 요청:

> "매주 월요일 오전 10시에 담당 사건들을 lawyer-mcp로 조회해서 `C:\Users\<사용자명>\Claude\Projects\사건조회\사건추적표.xlsx`에 누적하는 스케줄 작업을 만들어줘. 프롬프트는 아래 내용을 써줘."

그리고 **부록 B**의 프롬프트(경로 2곳만 새 PC로 수정)를 붙여넣으면 됩니다. cron은 `0 10 * * 1`.

> 또는: 현재 PC의 `C:\Users\<사용자명>\Claude\Scheduled\weekly-case-status-report\` 폴더를 새 PC의 `C:\Users\<사용자명>\Claude\Scheduled\`로 복사한 뒤, 그 안 `SKILL.md`의 경로 2곳(추적표 경로, 캡차 폴더 경로)만 새 PC 기준으로 수정해도 됩니다.

---

## 6. (새 PC) 검증

1. Cowork 채팅에서 실제 사건 한 건으로 테스트: "lawyer-mcp로 [법원명] [사건번호], 당사자 [당사자명] 조회해줘."
   → 캡차 이미지가 `_captcha`에 저장되고, 당사자·기일 등 결과가 나오면 성공.
2. 사이드바 **Scheduled → 해당 작업 → Run now** 1회 실행 → 도구·폴더 접근을 미리 승인. (이후 자동 실행이 멈추지 않음)

---

## 경로 치환 표 (현재 PC → 새 PC)

| 항목 | 현재 PC | 새 PC에서 바꿀 값 |
|---|---|---|
| lawyer-mcp 소스 | `<현재 PC의 소스 폴더>` | `C:\Users\<사용자명>\HwangsLawyerMCP` |
| 캡차 저장 폴더 | `<소스>\.captcha` | `C:\Users\<사용자명>\Claude\Projects\사건조회\_captcha` (env로 지정) |
| Cowork 작업폴더 | `C:\Users\<현재 사용자명>\Claude\Projects\사건조회` | `C:\Users\<사용자명>\Claude\Projects\사건조회` |
| 추적표 파일 | `<작업폴더>\사건추적표.xlsx` | 동일(이름 유지) |
| 스케줄 SKILL | `C:\Users\<현재 사용자명>\Claude\Scheduled\weekly-case-status-report\SKILL.md` | `C:\Users\<사용자명>\Claude\Scheduled\...` |

---

## 핵심 주의사항

- **법원명 입력 규칙**(case_search): 시·군법원은 단축명(`여수시법원`), 지원/본원은 풀네임(`광주지방법원 순천지원`). 단축명으로 지원을 넣으면 매칭 실패로 타임아웃.
- **캡차 자동 처리**: 경매(타경)는 캡차가 없어 완전 자동. 민사·자 사건은 Cowork의 Claude가 캡차 이미지를 읽어 입력 → `LAWYER_MCP_CAPTCHA_DIR`가 연결된(읽기 가능한) 폴더여야 자동 실행이 됩니다.
- **재시작 필요**: 소스를 고치거나 커넥터를 추가/수정하면 Claude Desktop(또는 해당 커넥터)을 재시작해야 반영됩니다.

---

## 부록 A — scourt.py 패치 (직접 적용용)

파일: `src/lawyer_mcp/scourt.py`

**(1) CAPTCHA 저장 디렉터리 기본값** — `import` 아래 상수부:

```python
# 변경 전
_CAPTCHA_DIR = os.environ.get("LAWYER_MCP_CAPTCHA_DIR", os.getcwd())

# 변경 후
_REPO_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
_CAPTCHA_DIR = os.environ.get("LAWYER_MCP_CAPTCHA_DIR") or os.path.join(
    _REPO_ROOT, ".captcha"
)
os.makedirs(_CAPTCHA_DIR, exist_ok=True)
```

**(2) 페이지 이동 대기 조건** — `start_challenge()` 안:

```python
# 변경 전
await page.goto(SEARCH_URL, wait_until="networkidle")

# 변경 후
await page.goto(SEARCH_URL, wait_until="domcontentloaded", timeout=30000)
```

이유: (1) 기본 cwd가 `C:\Windows\System32`라 캡차 저장 시 권한오류(EACCES) → 쓰기 가능한 폴더로. (2) 정부 사이트(WebSquare)는 네트워크가 계속 돌아 `networkidle`에 도달 못 해 타임아웃 → `domcontentloaded`로.

---

[3단계 Excel 갱신] 스냅샷의 현재상태/다음기일/계류지점/최근조회일 갱신, 부제 '최종 갱신' 날짜 갱신. "주차별 추적 로그"에 오늘 일자로 전체 사건 1행씩 append(변동사항 명시). 저장.

[4단계 보고] present_files로 xlsx 제시 + 채팅 3~6줄: 경매 상태 / 14일 내 임박 기일 D-day / 이번 주 신규 종국 / 수동확인 필요 사건.
```

> 위 프롬프트에서 바꿀 곳: **추적 파일 경로**(`C:\Users\<사용자명>\...`) 한 곳. 캡차는 커넥터 env(`LAWYER_MCP_CAPTCHA_DIR`)로 작업폴더 안에 저장되므로 프롬프트에 별도 경로가 없어도 됩니다.
