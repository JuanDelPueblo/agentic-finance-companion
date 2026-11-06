from collections.abc import AsyncIterator, Iterator

import httpx
import pytest

from app.config import get_settings
from app.db import get_engine, get_sessionmaker
from app.integrations.auth import get_auth
from app.integrations.llm import get_llm
from app.integrations.plaid import get_plaid

CACHED = (get_settings, get_engine, get_sessionmaker, get_auth, get_llm, get_plaid)


@pytest.fixture(autouse=True)
def isolated_settings(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Every test starts from mock providers, ignoring any developer `.env` values."""
    for name in ("AUTH_PROVIDER", "PLAID_PROVIDER", "LLM_PROVIDER"):
        monkeypatch.setenv(name, "mock")
    monkeypatch.setenv("APP_ENV", "test")
    for fn in CACHED:
        fn.cache_clear()
    yield
    for fn in CACHED:
        fn.cache_clear()


@pytest.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    from app.main import create_app

    transport = httpx.ASGITransport(app=create_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
