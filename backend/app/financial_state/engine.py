from uuid import UUID
from decimal import Decimal
from calendar import monthrange
from datetime import datetime, timedelta, date
from sqlalchemy import select

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Account, PlaidItem, Transaction
from app.financial_state.schemas import (
    AvailableCashForCurrency, 
    AvailableCashSummary,
    MonthlyIncomeForCurrency,
    MonthlyIncomeSummary
)

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


async def _get_monthly_income_rows(
    session: AsyncSession,
    user_id: UUID,
    month: date,
):
    month_start = month.replace(day=1) # date(2026, 11, 1) 11 being the month
    days_in_month = monthrange(month_start.year, month_start.month)[1] # (6,30) 6 Sunday, Month has 30 days
    next_month = month_start + timedelta(days=days_in_month) 

    result = await session.execute(
        select(Account.currency_code, Transaction.amount)
        .select_from(Transaction)
        .join(Account, Transaction.account_id == Account.account_id)
        .join(PlaidItem, Account.item_id == PlaidItem.item_id)
        .where(
            PlaidItem.user_id == user_id,
            Transaction.posted_date >= month_start,
            Transaction.posted_date < next_month,
            Transaction.sync_state == "posted",
            Transaction.category == "INCOME",
            Transaction.amount < 0, # Inflows are negative 
        )
    )

    return result.all()


async def get_available_cash(session: AsyncSession, user_id: UUID):
    result = await session.execute(
        select(
            Account.currency_code,
            Account.available_balance,
            PlaidItem.last_synced_at,
        )
        .join(PlaidItem, Account.item_id == PlaidItem.item_id)
        .where(
            PlaidItem.user_id == user_id,
            Account.account_type == "depository"
        )
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
        accounts_by_currency[currency_code].append(
            (available_cash, last_synced_at)
        )

    # Pack it in pydantic schemas
    by_currency_schema = []
    for currency_code, accounts in accounts_by_currency.items():
        known_balances = [
            balance for balance, _ in accounts if balance is not None
        ]
        included_accounts = len(known_balances)

        # Accounts with unknown balance
        missing_balance_accounts = len(accounts) - included_accounts

        if known_balances:
            amount = sum(known_balances, Decimal("0"))
        else:
            amount = None

        by_currency_schema.append(
            AvailableCashForCurrency(
                currency_code=currency_code,
                amount = amount,
                included_accounts=included_accounts,
                missing_balance_accounts=missing_balance_accounts,
                oldest_sync_at=_oldest_sync_at(accounts)
            )
        )

    # Return the Available Cash Summary
    return AvailableCashSummary(
        by_currency=by_currency_schema,
        unknown_currency_accounts=unknown_currency_accounts
    )

async def get_monthly_income(
    session: AsyncSession,
    user_id: UUID,
    month: date,
) -> MonthlyIncomeSummary:
    rows = await _get_monthly_income_rows(session, user_id, month)

    amounts_by_currency: dict[str, list[Decimal]] = {}
    unknown_currency_transactions = 0

    for currency_code, amount in rows:
        if currency_code is None:
            unknown_currency_transactions += 1
            continue

        if currency_code not in amounts_by_currency:
            amounts_by_currency[currency_code] = []
        else:
            amounts_by_currency[currency_code].append(-amount)

    by_currency_schemas = [
        MonthlyIncomeForCurrency(
            currency_code=currency_code,
            amount=sum(amounts, Decimal("0")),
            included_transactions=len(amounts),
        )
        for currency_code, amounts in amounts_by_currency.items()
    ]

    return MonthlyIncomeSummary(
        month=month.replace(day=1),
        by_currency=by_currency_schemas,
        unknown_currency_transactions=unknown_currency_transactions,
    )
