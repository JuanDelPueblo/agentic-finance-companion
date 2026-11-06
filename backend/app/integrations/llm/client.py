"""HTTP client for OpenAI-style (/chat/completions) and Anthropic-style (/messages) APIs.

Many hosted providers expose one or both of these protocols, so the provider is chosen
purely by configuration: base URL, API key, model, and `style`.
"""

import json
import logging
import re
from typing import Any, Literal

import httpx
from pydantic import BaseModel, ValidationError

from app.integrations.llm.base import (
    LLMError,
    LLMOutputError,
    LLMProviderError,
    LLMRequest,
    LLMTimeoutError,
)

logger = logging.getLogger(__name__)

ANTHROPIC_VERSION = "2023-06-01"
_FENCE = re.compile(r"^```(?:json)?\s*(.*?)\s*```$", re.DOTALL)


class HTTPLLMClient:
    def __init__(
        self,
        *,
        style: Literal["openai", "anthropic"],
        base_url: str,
        api_key: str,
        model: str,
        timeout_seconds: float = 30.0,
        max_retries: int = 2,  # the proposal allows at most two retries
        max_tokens: int = 4096,
        http: httpx.AsyncClient | None = None,
    ) -> None:
        self.style = style
        self.name = f"{style}-compatible"
        self.model = model
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._max_retries = max_retries
        self._max_tokens = max_tokens
        self._http = http or httpx.AsyncClient(timeout=timeout_seconds)

    async def generate[T: BaseModel](self, request: LLMRequest, output_type: type[T]) -> T:
        system = _with_schema_instructions(request.system, output_type)
        last_error: LLMError | None = None
        for attempt in range(self._max_retries + 1):
            try:
                text = await self._complete(system, request)
                return _parse_output(text, output_type)
            except LLMProviderError as exc:
                if not exc.retryable:
                    raise
                last_error = exc
            except (LLMTimeoutError, LLMOutputError) as exc:
                last_error = exc
            logger.warning("LLM attempt %d failed: %s", attempt + 1, last_error)
        assert last_error is not None
        raise last_error

    async def _complete(self, system: str, request: LLMRequest) -> str:
        messages = [m.model_dump() for m in request.messages]
        if self.style == "openai":
            url = f"{self._base_url}/chat/completions"
            headers = {"Authorization": f"Bearer {self._api_key}"}
            body: dict[str, Any] = {
                "model": self.model,
                "messages": [{"role": "system", "content": system}, *messages],
                "temperature": request.temperature,
                "max_tokens": self._max_tokens,
                "response_format": {"type": "json_object"},
            }
        else:
            url = f"{self._base_url}/messages"
            headers = {"x-api-key": self._api_key, "anthropic-version": ANTHROPIC_VERSION}
            body = {
                "model": self.model,
                "system": system,
                "messages": messages,
                "temperature": request.temperature,
                "max_tokens": self._max_tokens,
            }

        try:
            response = await self._http.post(url, json=body, headers=headers)
        except httpx.TimeoutException as exc:
            raise LLMTimeoutError(f"LLM request timed out: {exc}") from exc
        except httpx.HTTPError as exc:
            raise LLMProviderError(f"LLM transport error: {exc}") from exc
        if response.is_error:
            raise LLMProviderError(
                f"LLM provider returned HTTP {response.status_code}: {response.text[:300]}",
                status_code=response.status_code,
            )
        try:
            data = response.json()
            if self.style == "openai":
                return str(data["choices"][0]["message"]["content"])
            return "".join(b["text"] for b in data["content"] if b.get("type") == "text")
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise LLMOutputError(f"Unexpected response shape: {exc}") from exc


def _with_schema_instructions(system: str, output_type: type[BaseModel]) -> str:
    schema = json.dumps(output_type.model_json_schema(), separators=(",", ":"))
    return (
        f"{system}\n\nRespond with a single JSON object only, no prose, "
        f"matching this JSON Schema:\n{schema}"
    )


def _parse_output[T: BaseModel](text: str, output_type: type[T]) -> T:
    text = text.strip()
    if match := _FENCE.match(text):
        text = match.group(1)
    try:
        return output_type.model_validate_json(text)
    except ValidationError as exc:
        raise LLMOutputError(f"Output failed schema validation: {exc}") from exc
