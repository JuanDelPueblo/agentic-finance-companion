from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.financial_state.engine import get_monthly_spending
from app.models import Account, PlaidItem, Transaction
from app.plaid import sync
from tests.test_financial_state import add_account, add_item, add_user

pytestmark = pytest.mark.anyio


def plaid_transaction(account: Account, transaction_id: str, **fields: Any) -> dict[str, Any]:
    """A transaction as it appears in a /transactions/sync page, after to_dict()."""
    return {
        "transaction_id": transaction_id,
        "account_id": account.plaid_account_ref,
        "amount": 50.0,
        "date": date(2026, 11, 3),
        "name": "Campus Store",
        "merchant_name": "Campus Store",
        "pending": False,
        "personal_finance_category": {
            "primary": "GENERAL_MERCHANDISE",
            "detailed": "GENERAL_MERCHANDISE_BOOKSTORES_AND_NEWSSTANDS",
        },
        "transaction_code": "purchase",
        **fields,
    }


@pytest.fixture
def plaid_pages(monkeypatch) -> list[dict[str, Any]]:
    """Replaces the Plaid API; each sync call returns the next queued page."""
    pages: list[dict[str, Any]] = []

    async def fake_call(_method, _request):
        return SimpleNamespace(to_dict=lambda: pages.pop(0))

    monkeypatch.setattr(sync, "call", fake_call)
    monkeypatch.setattr(sync, "get_plaid", lambda: SimpleNamespace(transactions_sync=None))
    return pages


def page(added=(), modified=(), removed=(), cursor="cursor-1") -> dict[str, Any]:
    return {
        "added": list(added),
        "modified": list(modified),
        "removed": list(removed),
        "next_cursor": cursor,
        "has_more": False,
    }


async def synced_transactions(session: AsyncSession, item: PlaidItem) -> list[Transaction]:
    await sync._sync_transactions(session, item, access_token="access-sandbox-test")
    await session.flush()
    rows = await session.scalars(
        select(Transaction).join(Account).where(Account.item_id == item.item_id)
    )
    return list(rows)


async def test_sync_stores_the_transaction_code_and_both_categories(
    session: AsyncSession, plaid_pages: list
) -> None:
    item = await add_item(session, await add_user(session))
    account = await add_account(session, item, "0.00")
    plaid_pages.append(page(added=[plaid_transaction(account, "t1")]))

    [row] = await synced_transactions(session, item)

    assert row.transaction_code == "purchase"
    assert row.category == "GENERAL_MERCHANDISE"
    assert row.category_detailed == "GENERAL_MERCHANDISE_BOOKSTORES_AND_NEWSSTANDS"


async def test_sync_updates_the_fields_of_a_modified_transaction(
    session: AsyncSession, plaid_pages: list
) -> None:
    item = await add_item(session, await add_user(session))
    account = await add_account(session, item, "0.00")
    plaid_pages.append(page(added=[plaid_transaction(account, "t1")]))
    await synced_transactions(session, item)
    plaid_pages.append(
        page(
            modified=[
                plaid_transaction(
                    account,
                    "t1",
                    amount=-50.0,
                    transaction_code="refund",
                    personal_finance_category={
                        "primary": "GENERAL_MERCHANDISE",
                        "detailed": "GENERAL_MERCHANDISE_OTHER_GENERAL_MERCHANDISE",
                    },
                )
            ],
            cursor="cursor-2",
        )
    )

    [row] = await synced_transactions(session, item)

    assert row.transaction_code == "refund"
    assert row.category_detailed == "GENERAL_MERCHANDISE_OTHER_GENERAL_MERCHANDISE"
    assert item.sync_cursor == "cursor-2"


async def test_sync_stores_missing_fields_as_null(session: AsyncSession, plaid_pages: list) -> None:
    item = await add_item(session, await add_user(session))
    account = await add_account(session, item, "0.00")
    plaid_pages.append(
        page(
            added=[
                plaid_transaction(
                    account, "t1", transaction_code=None, personal_finance_category=None
                )
            ]
        )
    )

    [row] = await synced_transactions(session, item)

    assert row.transaction_code is None
    assert row.category is None
    assert row.category_detailed is None


async def test_a_synced_refund_lowers_monthly_spending(
    session: AsyncSession, plaid_pages: list
) -> None:
    user = await add_user(session)
    item = await add_item(session, user)
    account = await add_account(session, item, "0.00")
    plaid_pages.append(
        page(
            added=[
                plaid_transaction(account, "purchase", amount=50.0),
                plaid_transaction(account, "refund", amount=-20.0, transaction_code="refund"),
            ]
        )
    )
    await synced_transactions(session, item)

    summary = await get_monthly_spending(session, user.user_id, date(2026, 11, 1))

    [usd] = summary.by_currency
    assert usd.amount == Decimal("30.00")
    assert usd.included_transactions == 2
