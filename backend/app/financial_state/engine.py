from calendar import monthrange
from datetime import date, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.financial_state.schemas import (
    AvailableCashForCurrency,
    AvailableCashSummary,
    CategoryBreakdownForCurrency,
    CategoryBreakdownSummary,
    CreditBalanceOwedForCurrency,
    CreditBalanceOwedSummary,
    MonthlyAmountForCurrency,
    MonthlyAmountSummary,
    MonthlyNetCashFlowForCurrency,
    MonthlyNetCashFlowSummary,
    SpendingCategory,
)
from app.models import Account, PlaidItem, Transaction

_SPENDING_EXCLUDED_CATEGORIES = {"INCOME", "TRANSFER_IN", "TRANSFER_OUT"}


def _oldest_sync_at(
    accounts: list[tuple[Decimal | None, datetime | None]],
) -> datetime | None:
    sync_times: list[datetime] = []

    for balance, synced_at in accounts:
        if balance is None:
            continue
        if synced_at is None:
            return None

        sync_times.append(synced_at)

    return min(sync_times, default=None)


async def _get_monthly_transaction_rows(
    session: AsyncSession,
    user_id: UUID,
    month: date,
    *,
    income_only: bool = False,
):
    month_start = month.replace(day=1)  # date(2026, 11, 1) 11 being the month
    # monthrange returns (first weekday, days in month), e.g. (6, 30).
    days_in_month = monthrange(month_start.year, month_start.month)[1]
    next_month = month_start + timedelta(days=days_in_month)

    query = (
        select(
            Account.currency_code,
            Transaction.amount,
            Transaction.category,
            Transaction.transaction_code,
        )
        .select_from(Transaction)
        .join(Account, Transaction.account_id == Account.account_id)
        .join(PlaidItem, Account.item_id == PlaidItem.item_id)
        .where(
            PlaidItem.user_id == user_id,
            Transaction.posted_date >= month_start,
            Transaction.posted_date < next_month,
            Transaction.sync_state == "posted",
        )
    )

    if income_only:
        query = query.where(
            Transaction.category == "INCOME",
            Transaction.amount < 0,
        )

    result = await session.execute(query)

    return result.all()


async def get_available_cash(session: AsyncSession, user_id: UUID):
    result = await session.execute(
        select(
            Account.currency_code,
            Account.available_balance,
            PlaidItem.last_synced_at,
        )
        .join(PlaidItem, Account.item_id == PlaidItem.item_id)
        .where(PlaidItem.user_id == user_id, Account.account_type == "depository")
    )
    # Returns a tuple with:
    #  ("CAD", Decimal("1250.75"), datetime(2026, 11, 8, 10, 0, tzinfo=UTC)),

    # Accounts with unknown currency
    unknown_currency_accounts = 0

    # Organize the needed data per currency
    accounts_by_currency = {}
    for currency_code, available_cash, last_synced_at in result.all():
        if currency_code is None:
            unknown_currency_accounts += 1
            continue

        # If currency code not seen yet create it a list
        if currency_code not in accounts_by_currency:
            accounts_by_currency[currency_code] = []

        # If currency seen, append to the currency list
        accounts_by_currency[currency_code].append((available_cash, last_synced_at))

    # Pack it in pydantic schemas
    by_currency_schemas = []
    for currency_code, accounts in accounts_by_currency.items():
        known_balances = [balance for balance, _ in accounts if balance is not None]
        included_accounts = len(known_balances)

        # Accounts with unknown balance
        missing_balance_accounts = len(accounts) - included_accounts

        if known_balances:
            amount = sum(known_balances, Decimal("0"))
        else:
            amount = None

        by_currency_schemas.append(
            AvailableCashForCurrency(
                currency_code=currency_code,
                amount=amount,
                included_accounts=included_accounts,
                missing_balance_accounts=missing_balance_accounts,
                oldest_sync_at=_oldest_sync_at(accounts),
            )
        )

    # Return the Available Cash Summary
    return AvailableCashSummary(
        by_currency=by_currency_schemas, unknown_currency_accounts=unknown_currency_accounts
    )


async def get_credit_balance_owed(session: AsyncSession, user_id: UUID) -> CreditBalanceOwedSummary:
    result = await session.execute(
        select(
            Account.currency_code,
            Account.current_balance,
            PlaidItem.last_synced_at,
        )
        .join(PlaidItem, Account.item_id == PlaidItem.item_id)
        .where(PlaidItem.user_id == user_id, Account.account_type == "credit")
    )

    accounts_by_currency: dict[str, list[tuple[Decimal | None, datetime | None]]] = {}
    unknown_currency_accounts = 0
    for currency_code, balance, last_synced_at in result.all():
        if currency_code is None:
            unknown_currency_accounts += 1
            continue

        accounts_by_currency.setdefault(currency_code, []).append((balance, last_synced_at))

    zero = Decimal("0")
    by_currency_schemas = []
    for currency_code, accounts in sorted(accounts_by_currency.items()):
        known_balances = [balance for balance, _ in accounts if balance is not None]
        amount = sum((max(balance, zero) for balance in known_balances), zero)
        by_currency_schemas.append(
            CreditBalanceOwedForCurrency(
                currency_code=currency_code,
                amount=amount if known_balances else None,
                included_accounts=len(known_balances),
                missing_balance_accounts=len(accounts) - len(known_balances),
                oldest_sync_at=_oldest_sync_at(accounts),
            )
        )

    return CreditBalanceOwedSummary(
        by_currency=by_currency_schemas,
        unknown_currency_accounts=unknown_currency_accounts,
    )


async def get_monthly_income(
    session: AsyncSession,
    user_id: UUID,
    month: date,
) -> MonthlyAmountSummary:
    rows = await _get_monthly_transaction_rows(session, user_id, month, income_only=True)

    amounts_by_currency: dict[str, list[Decimal]] = {}
    unknown_currency_transactions = 0

    for currency_code, amount, _, _ in rows:
        if currency_code is None:
            unknown_currency_transactions += 1
            continue

        # Plaid reports inflows as negative amounts, so flip the sign.
        amounts_by_currency.setdefault(currency_code, []).append(-amount)

    by_currency_schemas = [
        MonthlyAmountForCurrency(
            currency_code=currency_code,
            amount=sum(amounts, Decimal("0")),
            included_transactions=len(amounts),
        )
        for currency_code, amounts in amounts_by_currency.items()
    ]

    return MonthlyAmountSummary(
        month=month.replace(day=1),
        by_currency=by_currency_schemas,
        unknown_currency_transactions=unknown_currency_transactions,
    )


def _is_monthly_spending(
    amount: Decimal, category: str | None, transaction_code: str | None
) -> bool:
    if amount < 0 and transaction_code == "refund":
        return True

    return amount > 0 and category not in _SPENDING_EXCLUDED_CATEGORIES


async def _group_monthly_spending(
    session: AsyncSession,
    user_id: UUID,
    month: date,
) -> tuple[dict[str, dict[str, list[Decimal]]], int]:
    rows = await _get_monthly_transaction_rows(session, user_id, month)

    spending_by_currency: dict[str, dict[str, list[Decimal]]] = {}
    unknown_currency_transactions = 0

    for currency_code, amount, category, transaction_code in rows:
        if not _is_monthly_spending(amount, category, transaction_code):
            continue

        if currency_code is None:
            unknown_currency_transactions += 1
            continue

        category_key = category or "UNCATEGORIZED"
        if category_key in _SPENDING_EXCLUDED_CATEGORIES:
            category_key = "UNCATEGORIZED"

        categories = spending_by_currency.setdefault(currency_code, {})
        categories.setdefault(category_key, []).append(amount)

    return spending_by_currency, unknown_currency_transactions


async def get_monthly_spending(
    session: AsyncSession,
    user_id: UUID,
    month: date,
) -> MonthlyAmountSummary:
    spending_by_currency, unknown_currency_transactions = await _group_monthly_spending(
        session, user_id, month
    )

    by_currency_schemas = []
    for currency_code, categories in spending_by_currency.items():
        amounts = [
            amount for category_amounts in categories.values() for amount in category_amounts
        ]
        by_currency_schemas.append(
            MonthlyAmountForCurrency(
                currency_code=currency_code,
                amount=sum(amounts, Decimal("0")),
                included_transactions=len(amounts),
            )
        )

    return MonthlyAmountSummary(
        month=month.replace(day=1),
        by_currency=by_currency_schemas,
        unknown_currency_transactions=unknown_currency_transactions,
    )


async def get_monthly_net_cash_flow(
    session: AsyncSession,
    user_id: UUID,
    month: date,
) -> MonthlyNetCashFlowSummary:
    rows = await _get_monthly_transaction_rows(session, user_id, month)
    totals_by_currency: dict[str, tuple[Decimal, Decimal, int]] = {}
    unknown_currency_transactions = 0
    zero = Decimal("0")

    for currency_code, amount, category, transaction_code in rows:
        is_income = category == "INCOME" and amount < 0
        if not is_income and not _is_monthly_spending(amount, category, transaction_code):
            continue

        if currency_code is None:
            unknown_currency_transactions += 1
            continue

        income, spending, count = totals_by_currency.get(currency_code, (zero, zero, 0))
        if is_income:
            income -= amount
        else:
            spending += amount
        totals_by_currency[currency_code] = (income, spending, count + 1)

    by_currency_schemas = [
        MonthlyNetCashFlowForCurrency(
            currency_code=currency_code,
            income=income,
            spending=spending,
            net_cash_flow=income - spending,
            included_transactions=count,
        )
        for currency_code, (income, spending, count) in sorted(totals_by_currency.items())
    ]

    return MonthlyNetCashFlowSummary(
        month=month.replace(day=1),
        by_currency=by_currency_schemas,
        unknown_currency_transactions=unknown_currency_transactions,
    )


async def get_category_breakdown(
    session: AsyncSession,
    user_id: UUID,
    month: date,
) -> CategoryBreakdownSummary:
    spending_by_currency, unknown_currency_transactions = await _group_monthly_spending(
        session, user_id, month
    )

    by_currency_schemas = []
    for currency_code, categories in spending_by_currency.items():
        category_totals = {
            category: sum(amounts, Decimal("0"))
            for category, amounts in categories.items()
        }
        currency_total = sum(category_totals.values(), Decimal("0"))

        category_rows = []
        for category, amount in category_totals.items():
            share_percent = float(amount / currency_total * 100) if currency_total else None
            category_rows.append(
                SpendingCategory(
                    category=category,
                    amount=amount,
                    included_transactions=len(categories[category]),
                    share_percent=share_percent,
                )
            )

        by_currency_schemas.append(
            CategoryBreakdownForCurrency(currency_code=currency_code, categories=category_rows)
        )

    return CategoryBreakdownSummary(
        month=month.replace(day=1),
        by_currency=by_currency_schemas,
        unknown_currency_transactions=unknown_currency_transactions,
    )
