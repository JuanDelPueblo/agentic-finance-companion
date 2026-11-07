from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", "../.env"), extra="ignore")

    database_url: str

    plaid_client_id: str | None = None
    plaid_sandbox_secret: SecretStr | None = None

@lru_cache
def get_engine() -> AsyncEngine:
    return create_async_engine(
        Settings().database_url,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=10,
    )

async def get_session():
    async with AsyncSession(get_engine()) as session:
        yield session