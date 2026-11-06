import httpx

from app.schemas.finance import Account, Transaction
from app.schemas.system import Health


async def test_health_reports_providers(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/health")
    assert response.status_code == 200
    health = Health.model_validate(response.json())
    assert {p.name: p.mode for p in health.providers} == {
        "auth": "mock",
        "plaid": "mock",
        "llm": "mock",
    }


async def test_stub_endpoints_match_contracts(client: httpx.AsyncClient) -> None:
    accounts = (await client.get("/api/accounts")).json()
    assert [Account.model_validate(a) for a in accounts]
    transactions = (await client.get("/api/transactions")).json()
    assert [Transaction.model_validate(t) for t in transactions]


async def test_money_is_serialized_as_exact_strings(client: httpx.AsyncClient) -> None:
    account = (await client.get("/api/accounts")).json()[0]
    assert account["current_balance"] == "842.17"
