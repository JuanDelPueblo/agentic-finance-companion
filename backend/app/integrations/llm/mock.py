"""LLM replacement that returns the output you register for each output type."""

from collections.abc import Callable
from typing import Any

from pydantic import BaseModel

from app.integrations.llm.base import LLMOutputError, LLMRequest

Responder = Callable[[LLMRequest], BaseModel | dict[str, Any]]


class MockLLM:
    name = "mock-llm"
    model = "mock"

    def __init__(self, responses: dict[type[BaseModel], Responder] | None = None) -> None:
        self._responses = dict(responses or {})
        self.requests: list[LLMRequest] = []  # inspect in tests

    async def generate[T: BaseModel](self, request: LLMRequest, output_type: type[T]) -> T:
        self.requests.append(request)
        responder = self._responses.get(output_type)
        if responder is None:
            raise LLMOutputError(f"MockLLM has no response for {output_type.__name__}")
        result = responder(request)
        data = result.model_dump() if isinstance(result, BaseModel) else result
        return output_type.model_validate(data)
