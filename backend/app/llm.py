"""Calls the hosted LLM and returns its reply as a validated Pydantic object.

LLM_PROVIDER picks Anthropic (the default) or OpenAI. Only the API call differs between
them; the retries, validation, and logging are shared. The SDK retries timeouts, rate
limits, server errors, and dropped connections. This module retries only replies it can't
use: cut off, not matching the schema, or failing `validate`.
"""

import logging
import time
from collections.abc import Callable
from functools import lru_cache
from typing import Any, Literal, NamedTuple

from anthropic import AsyncAnthropic, transform_schema
from openai import AsyncOpenAI
from pydantic import BaseModel, ValidationError

from app.db import Settings

logger = logging.getLogger(__name__)

TIMEOUT_SECONDS = 15.0
MAX_TOKENS = 16_000
# Retries for unusable replies, on top of the SDK's own retries for transport errors.
MAX_OUTPUT_RETRIES = 2
DEFAULT_MODELS = {"anthropic": "claude-haiku-5-5", "openai": "gpt-6-luna"}


class LLMError(Exception):
    """The LLM gave no usable reply. `reason` is "refusal" or "invalid_output"."""

    def __init__(self, reason: str, message: str) -> None:
        super().__init__(message)
        self.reason = reason


class Reply(NamedTuple):
    text: str
    stop: Literal["done", "refusal", "truncated"]
    input_tokens: int
    output_tokens: int


@lru_cache
def get_anthropic_client() -> AsyncAnthropic:
    key = Settings().anthropic_api_key
    if key is None:
        raise RuntimeError("Set ANTHROPIC_API_KEY to call the LLM")
    return AsyncAnthropic(api_key=key.get_secret_value(), timeout=TIMEOUT_SECONDS)


@lru_cache
def get_openai_client() -> AsyncOpenAI:
    key = Settings().openai_api_key
    if key is None:
        raise RuntimeError("Set OPENAI_API_KEY to call the LLM")
    return AsyncOpenAI(api_key=key.get_secret_value(), timeout=TIMEOUT_SECONDS)


async def _call_anthropic(
    model: str, system: str, messages: list[dict[str, str]], schema: dict[str, Any]
) -> Reply:
    response = await get_anthropic_client().messages.create(
        model=model,
        max_tokens=MAX_TOKENS,
        system=system,
        messages=messages,
        output_config={"format": {"type": "json_schema", "schema": schema}},
    )
    stops = {"refusal": "refusal", "max_tokens": "truncated"}
    return Reply(
        text="".join(block.text for block in response.content if block.type == "text"),
        stop=stops.get(response.stop_reason or "", "done"),
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
    )


async def _call_openai(
    model: str, system: str, messages: list[dict[str, str]], schema: dict[str, Any]
) -> Reply:
    response = await get_openai_client().chat.completions.create(
        model=model,
        max_completion_tokens=MAX_TOKENS,
        messages=[{"role": "system", "content": system}, *messages],
        response_format={
            "type": "json_schema",
            "json_schema": {"name": "reply", "schema": schema, "strict": True},
        },
    )
    choice = response.choices[0]
    if choice.message.refusal or choice.finish_reason == "content_filter":
        stop = "refusal"
    elif choice.finish_reason == "length":
        stop = "truncated"
    else:
        stop = "done"
    usage = response.usage
    return Reply(
        text=choice.message.content or "",
        stop=stop,
        input_tokens=usage.prompt_tokens if usage else 0,
        output_tokens=usage.completion_tokens if usage else 0,
    )


async def generate[T: BaseModel](
    system: str,
    context: BaseModel,
    output: type[T],
    validate: Callable[[T], list[str]] | None = None,
) -> T:
    """Ask the LLM for a reply that matches `output`.

    `context` must be a financial-state engine schema, never a database model, so the LLM
    only sees computed amounts and never account IDs or tokens. `validate` returns rule
    violations; when there are any, the LLM is asked again with the violations listed.
    """
    settings = Settings()
    provider = settings.llm_provider
    model = settings.llm_model or DEFAULT_MODELS[provider]
    call = _call_openai if provider == "openai" else _call_anthropic
    schema = transform_schema(output)
    messages: list[dict[str, str]] = [{"role": "user", "content": context.model_dump_json()}]

    for attempt in range(1, MAX_OUTPUT_RETRIES + 2):
        started = time.monotonic()
        reply = await call(model, system, messages, schema)
        logger.info(
            "LLM call provider=%s model=%s attempt=%d stop=%s seconds=%.2f "
            "input_tokens=%d output_tokens=%d",
            provider,
            model,
            attempt,
            reply.stop,
            time.monotonic() - started,
            reply.input_tokens,
            reply.output_tokens,
        )

        if reply.stop == "refusal":
            raise LLMError("refusal", "The LLM declined the request")

        text = reply.text
        if reply.stop == "truncated":
            problems = ["The reply was cut off. Reply with shorter JSON."]
        else:
            try:
                result = output.model_validate_json(text)
            except ValidationError as error:
                problems = [f"{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in error.errors()]
            else:
                problems = validate(result) if validate else []
                if not problems:
                    return result

        messages += [
            {"role": "assistant", "content": text or "(empty reply)"},
            {
                "role": "user",
                "content": "Your reply had these problems. Reply again with corrected JSON.\n"
                + "\n".join(f"- {problem}" for problem in problems),
            },
        ]

    raise LLMError(
        "invalid_output", f"No usable reply after {MAX_OUTPUT_RETRIES + 1} attempts: {problems}"
    )
