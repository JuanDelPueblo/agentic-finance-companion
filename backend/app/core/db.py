from collections.abc import AsyncIterator
from functools import lru_cache
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", "../.env"), extra="ignore")

    database_url: str

    # Backend JWT Token Functionality
    secret_key: SecretStr | None = None
    algorithm: Literal["HS256"] = "HS256"
    access_token_expire_min: int = 60

    plaid_client_id: str | None = None
    plaid_sandbox_secret: SecretStr | None = None
    plaid_webhook_url: str | None = None
    token_encryption_key: SecretStr | None = None

    llm_provider: Literal["anthropic", "openai"] = "anthropic"
    # Leave unset to use the provider's default model (see app/llm.py).
    llm_model: str | None = None
    anthropic_api_key: SecretStr | None = None
    openai_api_key: SecretStr | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()


@lru_cache
def get_engine() -> AsyncEngine:
    return create_async_engine(
        get_settings().database_url,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=10,
    )


async def get_session() -> AsyncIterator[AsyncSession]:
    # expire_on_commit=False keeps loaded attributes usable after a commit. In async code,
    # reloading an expired attribute raises an error.
    async with AsyncSession(get_engine(), expire_on_commit=False) as session:
        yield session
