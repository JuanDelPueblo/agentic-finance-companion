from collections.abc import AsyncIterator
from datetime import UTC, datetime
from unittest.mock import MagicMock
from uuid import UUID

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.dependencies import get_current_user_id
from app.main import app

pytestmark = pytest.mark.anyio
PREFIX = "/api/financial-state"


@pytest.fixture
async def client(monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[AsyncClient]:
    session = MagicMock(spec=AsyncSession)
    result = MagicMock()
    result.all.return_value = []
    session.execute.return_value = result
    monkeypatch.setitem(app.dependency_overrides, get_session, lambda: session)
    monkeypatch.setitem(app.dependency_overrides, get_current_user_id, lambda: UUID(int=1))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
        yield http


@pytest.mark.parametrize("route", ["available-cash", "credit-balance-owed"])
async def test_balance_endpoint(client: AsyncClient, route: str) -> None:
    response = await client.get(f"{PREFIX}/{route}")

    assert response.status_code == 200
    assert response.json() == {"by_currency": [], "unknown_currency_accounts": 0}


@pytest.mark.parametrize(
    "route",
    ["monthly-income", "net-monthly-spending", "net-monthly-cashflow", "category-breakdown"],
)
async def test_monthly_endpoint(client: AsyncClient, route: str) -> None:
    url = f"{PREFIX}/{route}"
    response = await client.get(url, params={"month": "2026-10-15"})

    assert response.status_code == 200
    assert response.json() == {
        "month": "2026-10-01",
        "by_currency": [],
        "unknown_currency_transactions": 0,
    }

    response = await client.get(url)
    assert response.status_code == 200
    assert response.json()["month"] == datetime.now(UTC).date().replace(day=1).isoformat()

    response = await client.get(url, params={"month": "2026-13-01"})
    assert response.status_code == 422
