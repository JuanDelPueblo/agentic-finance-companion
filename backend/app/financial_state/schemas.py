from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field, NonNegativeInt


class AvailableCashForCurrency(BaseModel):
    currency_code: str = Field(pattern=r"^[A-Z]{3}$")  # USD, CAD, etc
    amount: Decimal | None
    included_accounts: NonNegativeInt
    missing_balance_accounts: NonNegativeInt
    oldest_sync_at: datetime | None


class AvailableCashSummary(BaseModel):
    by_currency: list[AvailableCashForCurrency]
    unknown_currency_accounts: NonNegativeInt


class MonthlyAmountForCurrency(BaseModel):
    currency_code: str = Field(pattern=r"^[A-Z]{3}$")
    amount: Decimal
    included_transactions: NonNegativeInt


class MonthlyAmountSummary(BaseModel):
    month: date  # First day of requested month
    by_currency: list[MonthlyAmountForCurrency]
    unknown_currency_transactions: NonNegativeInt


class SpendingCategory(BaseModel):
    category: str
    amount: Decimal
    included_transactions: NonNegativeInt
    share_percent: float | None


class CategoryBreakdownForCurrency(BaseModel):
    currency_code: str = Field(pattern=r"^[A-Z]{3}$")
    categories: list[SpendingCategory]


class CategoryBreakdownSummary(BaseModel):
    month: date  # First day of requested month
    by_currency: list[CategoryBreakdownForCurrency]
    unknown_currency_transactions: NonNegativeInt
