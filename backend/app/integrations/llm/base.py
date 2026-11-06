"""Provider-neutral LLM interface: send a prompt, get a validated Pydantic object back."""

from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict


class LLMMessage(BaseModel):
    model_config = ConfigDict(frozen=True)

    role: Literal["user", "assistant"]
    content: str


class LLMRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    system: str
    messages: list[LLMMessage]
    temperature: float = 0.2


class LLMError(Exception):
    """Raised after all retries fail. The caller keeps the last valid plan."""


class LLMTimeoutError(LLMError):
    pass


class LLMProviderError(LLMError):
    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code

    @property
    def retryable(self) -> bool:
        return self.status_code is None or self.status_code == 429 or self.status_code >= 500


class LLMOutputError(LLMError):
    """The model replied, but the reply is not JSON that matches the requested schema."""


class LLMProvider(Protocol):
    name: str
    model: str

    async def generate[T: BaseModel](self, request: LLMRequest, output_type: type[T]) -> T: ...
