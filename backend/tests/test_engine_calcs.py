from datetime import UTC, date, datetime
from decimal import Decimal
from unittest.mock import MagicMock
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.financial_state.engine import (
    get_available_cash,
    get_category_breakdown,
    get_credit_balance_owed,
    get_monthly_income,
    get_monthly_net_cash_flow,
    get_monthly_spending,
)

pytestmark = pytest.mark.anyio

USER_ID = UUID(int=1)
REQUESTED_MONTH = date(2026, 11, 15)
MONTH_START = date(2026, 11, 1)

INCOME_ROWS = (
    ("USD", Decimal("-1200.00"), "INCOME", None),
    ("USD", Decimal("-350.50"), "INCOME", None),
    ("CAD", Decimal("-80.00"), "INCOME", None),
    (None, Decimal("-25.00"), "INCOME", None),
)

TRANSACTION_ROWS = (
    *INCOME_ROWS,
    ("USD", Decimal("120.25"), "FOOD_AND_DRINK", None),
    ("USD", Decimal("39.75"), "FOOD_AND_DRINK", None),
    ("USD", Decimal("-20.00"), "FOOD_AND_DRINK", "refund"),
    ("USD", Decimal("40.00"), "TRANSPORTATION", None),
    ("USD", Decimal("20.00"), None, None),
    ("CAD", Decimal("30.75"), "FOOD_AND_DRINK", None),
    ("CAD", Decimal("-5.75"), "FOOD_AND_DRINK", "refund"),
    (None, Decimal("12.50"), "FOOD_AND_DRINK", None),
    ("USD", Decimal("250.00"), "TRANSFER_OUT", None),
    ("USD", Decimal("-500.00"), "TRANSFER_IN", None),
    ("USD", Decimal("-60.00"), "FOOD_AND_DRINK", None),
    ("USD", Decimal("25.00"), "INCOME", None),
    (None, Decimal("10.00"), "TRANSFER_OUT", None),
)


def session_with_rows(*rows: tuple[object, ...]) -> AsyncSession:
    session = MagicMock(spec=AsyncSession)
    result = MagicMock()
    result.all.return_value = list(rows)
    session.execute.return_value = result
    return session


async def test_available_cash_adds_known_balances_by_currency() -> None:
    older_sync = datetime(2026, 11, 1, tzinfo=UTC)
    newer_sync = datetime(2026, 11, 8, tzinfo=UTC)
    session = session_with_rows(
        ("USD", Decimal("1200.75"), newer_sync),
        ("USD", Decimal("99.25"), older_sync),
        ("USD", None, None),
        ("CAD", Decimal("40.00"), newer_sync),
        (None, Decimal("999.00"), newer_sync),
    )

    summary = await get_available_cash(session, USER_ID)

    by_currency = {entry.currency_code: entry for entry in summary.by_currency}
    assert {code: entry.amount for code, entry in by_currency.items()} == {
        "USD": Decimal("1300.00"),
        "CAD": Decimal("40.00"),
    }
    assert by_currency["USD"].included_accounts == 2
    assert by_currency["USD"].missing_balance_accounts == 1
    assert by_currency["USD"].oldest_sync_at == older_sync
    assert summary.unknown_currency_accounts == 1


async def test_credit_balance_owed_adds_debts_without_offsetting_overpayments() -> None:
    session = session_with_rows(
        ("USD", Decimal("320.40"), None),
        ("USD", Decimal("79.60"), None),
        ("USD", Decimal("-45.00"), None),
        ("CAD", Decimal("-25.00"), None),
        ("EUR", None, None),
        (None, Decimal("50.00"), None),
    )

    summary = await get_credit_balance_owed(session, USER_ID)

    by_currency = {entry.currency_code: entry for entry in summary.by_currency}
    assert {code: entry.amount for code, entry in by_currency.items()} == {
        "USD": Decimal("400.00"),
        "CAD": Decimal("0.00"),
        "EUR": None,
    }
    assert by_currency["USD"].included_accounts == 3
    assert by_currency["EUR"].missing_balance_accounts == 1
    assert summary.unknown_currency_accounts == 1


async def test_monthly_income_reports_inflows_as_positive_amounts() -> None:
    # The income query selects only negative INCOME rows.
    session = session_with_rows(*INCOME_ROWS)

    summary = await get_monthly_income(session, USER_ID, REQUESTED_MONTH)

    assert summary.month == MONTH_START
    assert {
        entry.currency_code: (entry.amount, entry.included_transactions)
        for entry in summary.by_currency
    } == {"USD": (Decimal("1550.50"), 2), "CAD": (Decimal("80.00"), 1)}
    assert summary.unknown_currency_transactions == 1


async def test_monthly_spending_subtracts_refunds_and_excludes_transfers() -> None:
    session = session_with_rows(*TRANSACTION_ROWS)

    summary = await get_monthly_spending(session, USER_ID, REQUESTED_MONTH)

    assert summary.month == MONTH_START
    assert {
        entry.currency_code: (entry.amount, entry.included_transactions)
        for entry in summary.by_currency
    } == {"USD": (Decimal("200.00"), 5), "CAD": (Decimal("25.00"), 2)}
    assert summary.unknown_currency_transactions == 1


async def test_monthly_net_cash_flow_subtracts_spending_from_income() -> None:
    session = session_with_rows(*TRANSACTION_ROWS)

    summary = await get_monthly_net_cash_flow(session, USER_ID, REQUESTED_MONTH)

    assert summary.month == MONTH_START
    assert {
        entry.currency_code: (
            entry.income,
            entry.spending,
            entry.net_cash_flow,
            entry.included_transactions,
        )
        for entry in summary.by_currency
    } == {
        "USD": (Decimal("1550.50"), Decimal("200.00"), Decimal("1350.50"), 7),
        "CAD": (Decimal("80.00"), Decimal("25.00"), Decimal("55.00"), 3),
    }
    assert summary.unknown_currency_transactions == 2


async def test_category_breakdown_reports_net_amounts_and_shares_by_currency() -> None:
    session = session_with_rows(*TRANSACTION_ROWS)

    summary = await get_category_breakdown(session, USER_ID, REQUESTED_MONTH)

    assert summary.month == MONTH_START
    assert {
        entry.currency_code: {
            category.category: (
                category.amount,
                category.included_transactions,
                category.share_percent,
            )
            for category in entry.categories
        }
        for entry in summary.by_currency
    } == {
        "USD": {
            "FOOD_AND_DRINK": (Decimal("140.00"), 3, 70.0),
            "TRANSPORTATION": (Decimal("40.00"), 1, 20.0),
            "UNCATEGORIZED": (Decimal("20.00"), 1, 10.0),
        },
        "CAD": {"FOOD_AND_DRINK": (Decimal("25.00"), 2, 100.0)},
    }
    assert summary.unknown_currency_transactions == 1
