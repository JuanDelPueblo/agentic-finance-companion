from datetime import UTC, date, datetime
from decimal import Decimal
from itertools import count
from uuid import UUID

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.dependencies import get_current_user_id
from app.financial_state.engine import get_available_cash, get_monthly_income
from app.main import app
from app.models import Account, PlaidItem, Transaction, User

pytestmark = pytest.mark.anyio

_refs = count()


async def add_user(session: AsyncSession) -> User:
    user = User(email=f"user{next(_refs)}@example.com")
    session.add(user)
    await session.flush()
    return user


async def add_item(
    session: AsyncSession, user: User, last_synced_at: datetime | None = None
) -> PlaidItem:
    item = PlaidItem(
        user_id=user.user_id,
        plaid_item_ref=f"item-{next(_refs)}",
        access_token_encrypted="not-a-real-token",
        connection_status="healthy",
        last_synced_at=last_synced_at,
    )
    session.add(item)
    await session.flush()
    return item


async def add_account(
    session: AsyncSession,
    item: PlaidItem,
    available: str | None,
    currency: str | None = "USD",
    account_type: str = "depository",
) -> Account:
    account = Account(
        item_id=item.item_id,
        plaid_account_ref=f"account-{next(_refs)}",
        name="Checking",
        account_type=account_type,
        available_balance=None if available is None else Decimal(available),
        currency_code=currency,
    )
    session.add(account)
    await session.flush()
    return account


async def add_transaction(
    session: AsyncSession,
    account: Account,
    amount: str,
    posted: date,
    category: str | None = "INCOME",
    sync_state: str = "posted",
) -> Transaction:
    transaction = Transaction(
        account_id=account.account_id,
        plaid_transaction_ref=f"transaction-{next(_refs)}",
        amount=Decimal(amount),
        posted_date=posted,
        category=category,
        sync_state=sync_state,
    )
    session.add(transaction)
    await session.flush()
    return transaction


# Available cash


async def test_available_cash_with_no_accounts(session: AsyncSession) -> None:
    user = await add_user(session)

    summary = await get_available_cash(session, user.user_id)

    assert summary.by_currency == []
    assert summary.unknown_currency_accounts == 0


async def test_available_cash_sums_depository_accounts_per_currency(
    session: AsyncSession,
) -> None:
    user = await add_user(session)
    older = datetime(2026, 11, 1, 9, 0, tzinfo=UTC)
    newer = datetime(2026, 11, 8, 9, 0, tzinfo=UTC)
    first_item = await add_item(session, user, last_synced_at=newer)
    second_item = await add_item(session, user, last_synced_at=older)
    await add_account(session, first_item, "1250.75")
    await add_account(session, second_item, "100.10")
    await add_account(session, first_item, "40.00", currency="CAD")
    await add_account(session, first_item, None)  # balance not reported
    await add_account(session, first_item, "999.00", currency=None)
    await add_account(session, first_item, "5000.00", account_type="credit")

    summary = await get_available_cash(session, user.user_id)

    by_currency = {entry.currency_code: entry for entry in summary.by_currency}
    assert set(by_currency) == {"USD", "CAD"}
    assert by_currency["USD"].amount == Decimal("1350.85")
    assert by_currency["USD"].included_accounts == 2
    assert by_currency["USD"].missing_balance_accounts == 1
    assert by_currency["USD"].oldest_sync_at == older
    assert by_currency["CAD"].amount == Decimal("40.00")
    assert by_currency["CAD"].included_accounts == 1
    assert by_currency["CAD"].missing_balance_accounts == 0
    assert summary.unknown_currency_accounts == 1


async def test_available_cash_is_unknown_when_no_balance_is_reported(
    session: AsyncSession,
) -> None:
    user = await add_user(session)
    item = await add_item(session, user)
    await add_account(session, item, None)

    summary = await get_available_cash(session, user.user_id)

    [usd] = summary.by_currency
    assert usd.amount is None
    assert usd.included_accounts == 0
    assert usd.missing_balance_accounts == 1
    assert usd.oldest_sync_at is None


async def test_available_cash_ignores_other_users(session: AsyncSession) -> None:
    user = await add_user(session)
    other = await add_user(session)
    await add_account(session, await add_item(session, other), "500.00")

    summary = await get_available_cash(session, user.user_id)

    assert summary.by_currency == []


# Monthly income


async def test_monthly_income_counts_every_income_transaction(session: AsyncSession) -> None:
    # Regression test: the first transaction in each currency used to be dropped.
    user = await add_user(session)
    item = await add_item(session, user)
    usd = await add_account(session, item, "0.00")
    cad = await add_account(session, item, "0.00", currency="CAD")
    await add_transaction(session, usd, "-1200.00", date(2026, 11, 1))
    await add_transaction(session, usd, "-350.50", date(2026, 11, 15))
    await add_transaction(session, cad, "-80.00", date(2026, 11, 20))

    summary = await get_monthly_income(session, user.user_id, date(2026, 11, 1))

    by_currency = {entry.currency_code: entry for entry in summary.by_currency}
    assert by_currency["USD"].amount == Decimal("1550.50")
    assert by_currency["USD"].included_transactions == 2
    assert by_currency["CAD"].amount == Decimal("80.00")
    assert by_currency["CAD"].included_transactions == 1


async def test_monthly_income_excludes_transactions_that_are_not_posted_income(
    session: AsyncSession,
) -> None:
    user = await add_user(session)
    item = await add_item(session, user)
    account = await add_account(session, item, "0.00")
    day = date(2026, 11, 10)
    await add_transaction(session, account, "-500.00", day)  # the only one that counts
    await add_transaction(session, account, "-75.00", day, sync_state="pending")
    await add_transaction(session, account, "-40.00", day, category="TRANSFER_IN")
    await add_transaction(session, account, "-12.00", day, category=None)
    await add_transaction(session, account, "25.00", day)  # money out, not income

    summary = await get_monthly_income(session, user.user_id, day)

    [usd] = summary.by_currency
    assert usd.amount == Decimal("500.00")
    assert usd.included_transactions == 1


async def test_monthly_income_uses_calendar_month_bounds(session: AsyncSession) -> None:
    user = await add_user(session)
    item = await add_item(session, user)
    account = await add_account(session, item, "0.00")
    await add_transaction(session, account, "-1.00", date(2026, 11, 30))
    await add_transaction(session, account, "-10.00", date(2026, 12, 1))
    await add_transaction(session, account, "-100.00", date(2026, 12, 31))
    await add_transaction(session, account, "-1000.00", date(2027, 1, 1))

    summary = await get_monthly_income(session, user.user_id, date(2026, 12, 17))

    assert summary.month == date(2026, 12, 1)
    [usd] = summary.by_currency
    assert usd.amount == Decimal("110.00")
    assert usd.included_transactions == 2


async def test_monthly_income_counts_unknown_currency_separately(session: AsyncSession) -> None:
    user = await add_user(session)
    item = await add_item(session, user)
    account = await add_account(session, item, "0.00", currency=None)
    await add_transaction(session, account, "-300.00", date(2026, 11, 5))

    summary = await get_monthly_income(session, user.user_id, date(2026, 11, 1))

    assert summary.by_currency == []
    assert summary.unknown_currency_transactions == 1


async def test_monthly_income_ignores_other_users(session: AsyncSession) -> None:
    user = await add_user(session)
    other = await add_user(session)
    account = await add_account(session, await add_item(session, other), "0.00")
    await add_transaction(session, account, "-300.00", date(2026, 11, 5))

    summary = await get_monthly_income(session, user.user_id, date(2026, 11, 1))

    assert summary.by_currency == []


async def test_financial_state_is_reproducible(session: AsyncSession) -> None:
    user = await add_user(session)
    item = await add_item(session, user, last_synced_at=datetime(2026, 11, 8, tzinfo=UTC))
    account = await add_account(session, item, "321.09")
    await add_transaction(session, account, "-42.42", date(2026, 11, 3))

    first = (
        await get_available_cash(session, user.user_id),
        await get_monthly_income(session, user.user_id, date(2026, 11, 1)),
    )
    second = (
        await get_available_cash(session, user.user_id),
        await get_monthly_income(session, user.user_id, date(2026, 11, 1)),
    )

    assert [part.model_dump_json() for part in first] == [part.model_dump_json() for part in second]


# Endpoints


@pytest.fixture
async def client(session: AsyncSession):
    user = await add_user(session)

    async def override_session():
        yield session

    async def override_user_id() -> UUID:
        return user.user_id

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_current_user_id] = override_user_id
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as http_client:
            yield http_client, user
    finally:
        app.dependency_overrides.clear()


async def test_available_cash_endpoint(client, session: AsyncSession) -> None:
    http_client, user = client
    item = await add_item(session, user, last_synced_at=datetime(2026, 11, 8, tzinfo=UTC))
    await add_account(session, item, "1250.75")

    response = await http_client.get("/api/financial-state/available-cash")

    assert response.status_code == 200
    assert response.json() == {
        "by_currency": [
            {
                "currency_code": "USD",
                "amount": "1250.75",  # Decimals are sent as strings so no cents are lost.
                "included_accounts": 1,
                "missing_balance_accounts": 0,
                "oldest_sync_at": "2026-11-08T00:00:00Z",
            }
        ],
        "unknown_currency_accounts": 0,
    }


async def test_monthly_income_endpoint(client, session: AsyncSession) -> None:
    http_client, user = client
    account = await add_account(session, await add_item(session, user), "0.00")
    await add_transaction(session, account, "-1200.00", date(2026, 10, 1))
    await add_transaction(session, account, "-300.00", date(2026, 10, 31))

    response = await http_client.get(
        "/api/financial-state/monthly-income", params={"month": "2026-10-15"}
    )

    assert response.status_code == 200
    assert response.json() == {
        "month": "2026-10-01",
        "by_currency": [{"currency_code": "USD", "amount": "1500.00", "included_transactions": 2}],
        "unknown_currency_transactions": 0,
    }


async def test_monthly_income_endpoint_defaults_to_current_month(client) -> None:
    http_client, _user = client

    response = await http_client.get("/api/financial-state/monthly-income")

    assert response.status_code == 200
    assert response.json()["month"] == datetime.now(UTC).date().replace(day=1).isoformat()


async def test_monthly_income_endpoint_rejects_an_invalid_month(client) -> None:
    http_client, _user = client

    response = await http_client.get(
        "/api/financial-state/monthly-income", params={"month": "2026-13-01"}
    )

    assert response.status_code == 422
