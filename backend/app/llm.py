"""Calls the hosted LLM and returns its reply as a validated Pydantic object.

The SDK retries timeouts, rate limits, server errors, and dropped connections. This module
retries only replies it can't use: cut off, not matching the schema, or failing `validate`.
"""

import logging
import time
from collections.abc import Callable
from functools import lru_cache

from anthropic import AsyncAnthropic, transform_schema
from anthropic.types import MessageParam
from pydantic import BaseModel, ValidationError

from app.db import Settings

logger = logging.getLogger(__name__)

TIMEOUT_SECONDS = 15.0
MAX_TOKENS = 16_000
# Retries for unusable replies, on top of the SDK's own retries for transport errors.
MAX_OUTPUT_RETRIES = 2


class LLMError(Exception):
    """The LLM gave no usable reply. `reason` is "refusal" or "invalid_output"."""

    def __init__(self, reason: str, message: str) -> None:
        super().__init__(message)
        self.reason = reason


@lru_cache
def get_client() -> AsyncAnthropic:
    key = Settings().anthropic_api_key
    if key is None:
        raise RuntimeError("Set ANTHROPIC_API_KEY to call the LLM")
    return AsyncAnthropic(api_key=key.get_secret_value(), timeout=TIMEOUT_SECONDS)


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
    model = Settings().llm_model
    output_format = {"type": "json_schema", "schema": transform_schema(output)}
    messages: list[MessageParam] = [{"role": "user", "content": context.model_dump_json()}]

    for attempt in range(1, MAX_OUTPUT_RETRIES + 2):
        started = time.monotonic()
        response = await get_client().messages.create(
            model=model,
            max_tokens=MAX_TOKENS,
            system=system,
            messages=messages,
            output_config={"format": output_format},
        )
        logger.info(
            "LLM call model=%s attempt=%d stop_reason=%s seconds=%.2f "
            "input_tokens=%d output_tokens=%d",
            model,
            attempt,
            response.stop_reason,
            time.monotonic() - started,
            response.usage.input_tokens,
            response.usage.output_tokens,
        )

        if response.stop_reason == "refusal":
            raise LLMError("refusal", "The LLM declined the request")

        text = "".join(block.text for block in response.content if block.type == "text")
        if response.stop_reason == "max_tokens":
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
