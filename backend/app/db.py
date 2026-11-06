from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", "../.env"), extra="ignore")

    database_url: str = "postgresql+psycopg://finance:finance@localhost:5432/finance"


@lru_cache
def get_engine() -> AsyncEngine:
    return create_async_engine(Settings().database_url, pool_pre_ping=True)
