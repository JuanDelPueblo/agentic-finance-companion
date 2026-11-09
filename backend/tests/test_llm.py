import os
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from anthropic.types import Message, TextBlock, Usage
from openai.types import CompletionUsage
from openai.types.chat import ChatCompletion, ChatCompletionMessage
from openai.types.chat.chat_completion import Choice
from pydantic import BaseModel

from app import llm
from app.llm import LLMError, generate

pytestmark = pytest.mark.anyio


class Context(BaseModel):
    available_cash: str


class Reply(BaseModel):
    weekly_limit: int
    tip: str


def anthropic_reply(text: str, stop: str) -> Message:
    stop_reason = {"done": "end_turn", "refusal": "refusal", "truncated": "max_tokens"}[stop]
    return Message(
        id="msg_test",
        type="message",
        role="assistant",
        model="claude-haiku-5-5",
        content=[TextBlock(type="text", text=text)],
        stop_reason=stop_reason,
        usage=Usage(input_tokens=10, output_tokens=5),
    )


def openai_reply(text: str, stop: str) -> ChatCompletion:
    refused = stop == "refusal"
    return ChatCompletion(
        id="chatcmpl_test",
        object="chat.completion",
        created=0,
        model="gpt-6-luna",
        choices=[
            Choice(
                index=0,
                finish_reason="length" if stop == "truncated" else "stop",
                message=ChatCompletionMessage(
                    role="assistant",
                    content=None if refused else text,
                    refusal=text if refused else None,
                ),
            )
        ],
        usage=CompletionUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15),
    )


class FakeAPI:
    """Replaces one provider's API call. Queue replies with `replies`."""

    def __init__(self, provider: str, create: AsyncMock) -> None:
        self.provider = provider
        self.create = create

    def replies(self, *replies: tuple[str, str]) -> None:
        build = openai_reply if self.provider == "openai" else anthropic_reply
        self.create.side_effect = [build(text, stop) for text, stop in replies]

    def sent_messages(self) -> list[dict[str, str]]:
        """The conversation in the last request, without OpenAI's leading system message."""
        messages = self.create.call_args.kwargs["messages"]
        return messages[1:] if self.provider == "openai" else messages


@pytest.fixture(params=["anthropic", "openai"])
def api(request, monkeypatch) -> FakeAPI:
    provider = request.param
    monkeypatch.setenv("LLM_PROVIDER", provider)
    monkeypatch.delenv("LLM_MODEL", raising=False)
    create = AsyncMock()
    if provider == "openai":
        client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
        monkeypatch.setattr(llm, "get_openai_client", lambda: client)
    else:
        client = SimpleNamespace(messages=SimpleNamespace(create=create))
        monkeypatch.setattr(llm, "get_anthropic_client", lambda: client)
    return FakeAPI(provider, create)


VALID = '{"weekly_limit": 120, "tip": "Cook at home twice more."}'


async def test_returns_the_parsed_reply(api: FakeAPI) -> None:
    api.replies((VALID, "done"))

    result = await generate("Plan.", Context(available_cash="500.00"), Reply)

    assert result == Reply(weekly_limit=120, tip="Cook at home twice more.")
    request = api.create.call_args.kwargs
    assert request["model"] == llm.DEFAULT_MODELS[api.provider]
    assert api.sent_messages() == [{"role": "user", "content": '{"available_cash":"500.00"}'}]
    if api.provider == "openai":
        assert request["messages"][0] == {"role": "system", "content": "Plan."}
        schema = request["response_format"]["json_schema"]
        assert schema["strict"] is True
    else:
        assert request["system"] == "Plan."
        schema = request["output_config"]["format"]
    assert schema["schema"]["required"] == ["weekly_limit", "tip"]


async def test_uses_the_configured_model(api: FakeAPI, monkeypatch) -> None:
    monkeypatch.setenv("LLM_MODEL", "some-other-model")
    api.replies((VALID, "done"))

    await generate("Plan.", Context(available_cash="500.00"), Reply)

    assert api.create.call_args.kwargs["model"] == "some-other-model"


async def test_retries_a_reply_that_fails_validation_with_the_problems_listed(
    api: FakeAPI,
) -> None:
    api.replies(('{"weekly_limit": 900, "tip": "Spend it."}', "done"), (VALID, "done"))

    def validate(reply: Reply) -> list[str]:
        return ["weekly_limit exceeds available cash"] if reply.weekly_limit > 500 else []

    result = await generate("Plan.", Context(available_cash="500.00"), Reply, validate)

    assert result.weekly_limit == 120
    assert api.create.call_count == 2
    retry_messages = api.sent_messages()
    assert retry_messages[1] == {
        "role": "assistant",
        "content": '{"weekly_limit": 900, "tip": "Spend it."}',
    }
    assert "weekly_limit exceeds available cash" in retry_messages[2]["content"]


async def test_retries_a_reply_that_does_not_match_the_schema(api: FakeAPI) -> None:
    api.replies(('{"weekly_limit": "lots"}', "done"), (VALID, "done"))

    result = await generate("Plan.", Context(available_cash="500.00"), Reply)

    assert result.weekly_limit == 120
    problems = api.sent_messages()[2]["content"]
    assert "weekly_limit" in problems
    assert "tip" in problems


async def test_retries_a_reply_that_was_cut_off(api: FakeAPI) -> None:
    api.replies(('{"weekly_limit": 12', "truncated"), (VALID, "done"))

    result = await generate("Plan.", Context(available_cash="500.00"), Reply)

    assert result.weekly_limit == 120
    assert "cut off" in api.sent_messages()[2]["content"]


async def test_gives_up_after_two_retries(api: FakeAPI) -> None:
    api.replies(*[("not json", "done")] * 4)

    with pytest.raises(LLMError) as error:
        await generate("Plan.", Context(available_cash="500.00"), Reply)

    assert error.value.reason == "invalid_output"
    assert api.create.call_count == 3


async def test_does_not_retry_a_refusal(api: FakeAPI) -> None:
    api.replies(("I can't help with that.", "refusal"))

    with pytest.raises(LLMError) as error:
        await generate("Plan.", Context(available_cash="500.00"), Reply)

    assert error.value.reason == "refusal"
    assert api.create.call_count == 1


async def live_call() -> Reply:
    return await generate(
        "You help a college student budget. Suggest a weekly spending limit in whole dollars "
        "that is less than their available cash, and one short tip.",
        Context(available_cash="500.00"),
        Reply,
        lambda reply: [] if 0 < reply.weekly_limit < 500 else ["weekly_limit out of range"],
    )


@pytest.mark.skipif(not os.environ.get("ANTHROPIC_API_KEY"), reason="ANTHROPIC_API_KEY is not set")
async def test_live_anthropic_call_returns_a_valid_reply(monkeypatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    monkeypatch.delenv("LLM_MODEL", raising=False)
    llm.get_anthropic_client.cache_clear()

    result = await live_call()

    assert 0 < result.weekly_limit < 500
    assert result.tip


@pytest.mark.skipif(not os.environ.get("OPENAI_API_KEY"), reason="OPENAI_API_KEY is not set")
async def test_live_openai_call_returns_a_valid_reply(monkeypatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.delenv("LLM_MODEL", raising=False)
    llm.get_openai_client.cache_clear()

    result = await live_call()

    assert 0 < result.weekly_limit < 500
    assert result.tip
