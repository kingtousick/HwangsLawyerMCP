"""CAPTCHA 2단계 툴의 MCP 계약(인자·응답 필드 이름) 테스트.

원격 Cowork 중계가 툴 인자 중 `session_id` 키를 제거해 버려
case_search_submit 이 'session_id Field required' 로 실패한 적이 있다.
그래서 클라이언트에 노출되는 식별자 이름은 `challenge_id` 를 쓴다.
브라우저 없이 돌도록 scourt 쪽 함수는 대역으로 바꾼다.
"""

import asyncio
import json

from mcp.shared.memory import create_connected_server_and_client_session

from lawyer_mcp import scourt, server
from lawyer_mcp.models import CaptchaChallenge, CaseInfo

# 1x1 투명 PNG
_PNG = bytes.fromhex(
  "89504e470d0a1a0a0000000d4948445200000001000000010806000000"
  "1f15c4890000000d49444154789c63000100000500010d0a2db40000000049454e44ae426082"
)


def _call(tool: str, args: dict):
  async def run():
    async with create_connected_server_and_client_session(server.mcp._mcp_server) as client:
      return await client.call_tool(tool, args)

  return asyncio.run(run())


def _input_schema(tool: str) -> dict:
  async def run():
    async with create_connected_server_and_client_session(server.mcp._mcp_server) as client:
      tools = await client.list_tools()
      return next(t.inputSchema for t in tools.tools if t.name == tool)

  return asyncio.run(run())


class TestSubmitArguments:
  def test_uses_challenge_id_not_session_id(self):
    schema = _input_schema("case_search_submit")
    assert "challenge_id" in schema["required"]
    assert "session_id" not in schema["properties"]

  def test_challenge_id_reaches_submit_answer(self, monkeypatch):
    received = {}

    async def fake_submit(challenge_id, captcha_text):
      received.update(challenge_id=challenge_id, captcha_text=captcha_text)
      return CaseInfo(case_no="25자1", court="여수시법원")

    monkeypatch.setattr(scourt, "submit_answer", fake_submit)
    res = _call("case_search_submit", {"challenge_id": "abc123def456", "captcha_text": "123456"})

    assert not res.isError
    assert received == {"challenge_id": "abc123def456", "captcha_text": "123456"}


class TestCaptchaResponse:
  def test_returns_challenge_id_with_image(self, monkeypatch, tmp_path):
    img = tmp_path / "captcha_abc123def456.png"
    img.write_bytes(_PNG)

    async def fake_start(court, case_no, party_name):
      return CaptchaChallenge(challenge_id="abc123def456", captcha_image_path=str(img), message="m")

    monkeypatch.setattr(scourt, "start_challenge", fake_start)
    res = _call("case_search_captcha", {"court": "여수시법원", "case_no": "25자1", "party_name": "홍길동"})

    assert not res.isError
    assert [c.type for c in res.content] == ["image", "text"]
    payload = json.loads(res.content[1].text)
    assert payload["challenge_id"] == "abc123def456"
    assert "session_id" not in payload
