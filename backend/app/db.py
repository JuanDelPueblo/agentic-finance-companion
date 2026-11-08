from collections.abc import AsyncIterator
from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", "../.env"), extra="ignore")

    database_url: str

    plaid_client_id: str | None = None
    plaid_sandbox_secret: SecretStr | None = None
    plaid_webhook_url: str | None = None
    token_encryption_key: SecretStr | None = None

    anthropic_api_key: SecretStr | None = None
    llm_model: str = "claude-haiku-5-5"


@lru_cache
def get_engine() -> AsyncEngine:
    return create_async_engine(
        Settings().database_url,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=10,
    )


async def get_session() -> AsyncIterator[AsyncSession]:
    # expire_on_commit=False keeps loaded attributes usable after a commit. In async code,
    # reloading an expired attribute raises an error.
    async with AsyncSession(get_engine(), expire_on_commit=False) as session:
        yield session
