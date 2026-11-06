import json
from typing import Any, Literal

import httpx
import pytest
import respx
from pydantic import BaseModel

from app.integrations.llm import LLMMessage, LLMOutputError, LLMProviderError, LLMRequest
from app.integrations.llm.client import HTTPLLMClient
from app.integrations.llm.mock import MockLLM

BASE = "https://llm.example.test/v1"


class CandidatePlan(BaseModel):
    summary: str
    actions: list[str]


REQUEST = LLMRequest(
    system="You are a planning assistant.",
    messages=[LLMMessage(role="user", content="Make a plan.")],
)
PLAN = {"summary": "s", "actions": ["a"]}


def _client(style: Literal["openai", "anthropic"], **kwargs: Any) -> HTTPLLMClient:
    return HTTPLLMClient(
        style=style,
        base_url=BASE,
        api_key="key",
        model="deepseek-v4.1-flash",
        http=httpx.AsyncClient(),
        **kwargs,
    )


def _openai_reply(content: str) -> dict[str, Any]:
    return {"choices": [{"message": {"role": "assistant", "content": content}}]}


@respx.mock
async def test_openai_style() -> None:
    route = respx.post(f"{BASE}/chat/completions").respond(json=_openai_reply(json.dumps(PLAN)))
    plan = await _client("openai").generate(REQUEST, CandidatePlan)
    assert plan.summary == "s"
    sent = route.calls.last.request
    body = json.loads(sent.content)
    assert sent.headers["Authorization"] == "Bearer key"
    assert body["model"] == "deepseek-v4.1-flash"
    assert body["messages"][0]["role"] == "system"
    assert "JSON Schema" in body["messages"][0]["content"]
    assert body["response_format"] == {"type": "json_object"}


@respx.mock
async def test_anthropic_style_with_code_fence() -> None:
    route = respx.post(f"{BASE}/messages").respond(
        json={"content": [{"type": "text", "text": f"```json\n{json.dumps(PLAN)}\n```"}]}
    )
    plan = await _client("anthropic").generate(REQUEST, CandidatePlan)
    assert plan.actions == ["a"]
    sent = route.calls.last.request
    assert sent.headers["x-api-key"] == "key"
    assert sent.headers["anthropic-version"] == "2023-06-01"
    body = json.loads(sent.content)
    assert body["system"].startswith("You are a planning assistant.")
    assert body["messages"] == [{"role": "user", "content": "Make a plan."}]


@respx.mock
async def test_retries_invalid_output_then_succeeds() -> None:
    route = respx.post(f"{BASE}/chat/completions").mock(
        side_effect=[
            httpx.Response(200, json=_openai_reply("not json")),
            httpx.Response(503),
            httpx.Response(200, json=_openai_reply(json.dumps(PLAN))),
        ]
    )
    plan = await _client("openai", max_retries=2).generate(REQUEST, CandidatePlan)
    assert plan.summary == "s" and route.call_count == 3


@respx.mock
async def test_gives_up_after_max_retries() -> None:
    route = respx.post(f"{BASE}/chat/completions").respond(
        json=_openai_reply('{"summary": "missing fields"}')
    )
    with pytest.raises(LLMOutputError):
        await _client("openai", max_retries=2).generate(REQUEST, CandidatePlan)
    assert route.call_count == 3  # first attempt + 2 retries


@respx.mock
async def test_timeouts_are_retried() -> None:
    route = respx.post(f"{BASE}/chat/completions").mock(
        side_effect=[
            httpx.ReadTimeout("slow"),
            httpx.Response(200, json=_openai_reply(json.dumps(PLAN))),
        ]
    )
    await _client("openai").generate(REQUEST, CandidatePlan)
    assert route.call_count == 2


@respx.mock
async def test_auth_errors_are_not_retried() -> None:
    route = respx.post(f"{BASE}/chat/completions").respond(401, json={"error": "bad key"})
    with pytest.raises(LLMProviderError) as excinfo:
        await _client("openai").generate(REQUEST, CandidatePlan)
    assert excinfo.value.status_code == 401 and route.call_count == 1


async def test_mock_llm_returns_registered_response_and_records_requests() -> None:
    llm = MockLLM(responses={CandidatePlan: lambda _request: PLAN})
    plan = await llm.generate(REQUEST, CandidatePlan)
    assert plan.summary == "s"
    assert llm.requests == [REQUEST]


async def test_mock_llm_without_response_fails() -> None:
    with pytest.raises(LLMOutputError):
        await MockLLM().generate(REQUEST, CandidatePlan)
