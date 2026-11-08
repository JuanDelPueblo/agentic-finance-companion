import os
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from anthropic.types import Message, TextBlock, Usage
from pydantic import BaseModel

from app import llm
from app.llm import LLMError, generate

pytestmark = pytest.mark.anyio


class Context(BaseModel):
    available_cash: str


class Reply(BaseModel):
    weekly_limit: int
    tip: str


def message(text: str, stop_reason: str = "end_turn") -> Message:
    return Message(
        id="msg_test",
        type="message",
        role="assistant",
        model="claude-haiku-5-5",
        content=[TextBlock(type="text", text=text)],
        stop_reason=stop_reason,
        usage=Usage(input_tokens=10, output_tokens=5),
    )


@pytest.fixture
def create(monkeypatch) -> AsyncMock:
    """Replaces the API call; set `side_effect` to the replies the test needs."""
    mock = AsyncMock()
    client = SimpleNamespace(messages=SimpleNamespace(create=mock))
    monkeypatch.setattr(llm, "get_client", lambda: client)
    return mock


VALID = '{"weekly_limit": 120, "tip": "Cook at home twice more."}'


async def test_returns_the_parsed_reply(create: AsyncMock) -> None:
    create.side_effect = [message(VALID)]

    result = await generate("Plan.", Context(available_cash="500.00"), Reply)

    assert result == Reply(weekly_limit=120, tip="Cook at home twice more.")
    request = create.call_args.kwargs
    assert request["messages"] == [{"role": "user", "content": '{"available_cash":"500.00"}'}]
    assert request["output_config"]["format"]["type"] == "json_schema"
    assert request["output_config"]["format"]["schema"]["required"] == ["weekly_limit", "tip"]


async def test_retries_a_reply_that_fails_validation_with_the_problems_listed(
    create: AsyncMock,
) -> None:
    create.side_effect = [
        message('{"weekly_limit": 900, "tip": "Spend it."}'),
        message(VALID),
    ]

    def validate(reply: Reply) -> list[str]:
        return ["weekly_limit exceeds available cash"] if reply.weekly_limit > 500 else []

    result = await generate("Plan.", Context(available_cash="500.00"), Reply, validate)

    assert result.weekly_limit == 120
    assert create.call_count == 2
    retry_messages = create.call_args.kwargs["messages"]
    assert retry_messages[1] == {
        "role": "assistant",
        "content": '{"weekly_limit": 900, "tip": "Spend it."}',
    }
    assert "weekly_limit exceeds available cash" in retry_messages[2]["content"]


async def test_retries_a_reply_that_does_not_match_the_schema(create: AsyncMock) -> None:
    create.side_effect = [message('{"weekly_limit": "lots"}'), message(VALID)]

    result = await generate("Plan.", Context(available_cash="500.00"), Reply)

    assert result.weekly_limit == 120
    problems = create.call_args.kwargs["messages"][2]["content"]
    assert "weekly_limit" in problems
    assert "tip" in problems


async def test_retries_a_reply_that_was_cut_off(create: AsyncMock) -> None:
    create.side_effect = [message('{"weekly_limit": 12', stop_reason="max_tokens"), message(VALID)]

    result = await generate("Plan.", Context(available_cash="500.00"), Reply)

    assert result.weekly_limit == 120
    assert "cut off" in create.call_args.kwargs["messages"][2]["content"]


async def test_gives_up_after_two_retries(create: AsyncMock) -> None:
    create.side_effect = [message("not json")] * 4

    with pytest.raises(LLMError) as error:
        await generate("Plan.", Context(available_cash="500.00"), Reply)

    assert error.value.reason == "invalid_output"
    assert create.call_count == 3


async def test_does_not_retry_a_refusal(create: AsyncMock) -> None:
    create.side_effect = [message("I can't help with that.", stop_reason="refusal")]

    with pytest.raises(LLMError) as error:
        await generate("Plan.", Context(available_cash="500.00"), Reply)

    assert error.value.reason == "refusal"
    assert create.call_count == 1


@pytest.mark.skipif(not os.environ.get("ANTHROPIC_API_KEY"), reason="ANTHROPIC_API_KEY is not set")
async def test_live_call_returns_a_valid_reply() -> None:
    llm.get_client.cache_clear()
    result = await generate(
        "You help a college student budget. Suggest a weekly spending limit in whole dollars "
        "that is less than their available cash, and one short tip.",
        Context(available_cash="500.00"),
        Reply,
        lambda reply: [] if 0 < reply.weekly_limit < 500 else ["weekly_limit out of range"],
    )

    assert 0 < result.weekly_limit < 500
    assert result.tip
