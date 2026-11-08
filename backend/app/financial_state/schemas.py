from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field, NonNegativeInt


class AvailableCashForCurrency(BaseModel):
    currency_code: str = Field(pattern=r"[A-Z]{3}")  # USD, CAD, etc
    amount: Decimal | None
    included_accounts: NonNegativeInt
    missing_balance_accounts: NonNegativeInt
    oldest_sync_at: datetime | None


class AvailableCashSummary(BaseModel):
    by_currency = list[AvailableCashForCurrency]
    unknown_currency_accounts: NonNegativeInt


class MonthlyIncomeForCurrency(BaseModel):
    currency_code: str = Field(pattern=r"[A-Z]{3}")
    amount: Decimal
    included_transactions: NonNegativeInt


class MonthlyIncomeSummary(BaseModel):
    month: date  # First day of requested month
    by_currency: list[MonthlyIncomeForCurrency]
    unknown_currency_transactions: NonNegativeInt
