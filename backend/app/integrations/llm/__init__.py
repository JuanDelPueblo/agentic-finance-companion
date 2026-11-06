"""LLM integration. Business logic calls `get_llm().generate(request, OutputModel)`."""

from functools import lru_cache

from app.config import get_settings
from app.integrations.llm.base import (
    LLMError,
    LLMMessage,
    LLMOutputError,
    LLMProvider,
    LLMProviderError,
    LLMRequest,
    LLMTimeoutError,
)
from app.integrations.llm.client import HTTPLLMClient
from app.integrations.llm.mock import MockLLM

__all__ = [
    "LLMError",
    "LLMMessage",
    "LLMOutputError",
    "LLMProvider",
    "LLMProviderError",
    "LLMRequest",
    "LLMTimeoutError",
    "get_llm",
]


@lru_cache
def get_llm() -> LLMProvider:
    settings = get_settings()
    if settings.llm_provider == "mock":
        return MockLLM()
    return HTTPLLMClient(
        style=settings.llm_provider,
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key.get_secret_value(),
        model=settings.llm_model,
    )
