from decimal import Decimal
from datetime import datetime

from pydantic import BaseModel, Field, NonNegativeInt

class AvailableCashForCurrency(BaseModel):
    currency_code: str = Field(pattern=r"[A-Z]{4}") # USD, CAD, etc
    amount: Decimal | None
    included_accounts: NonNegativeInt
    missing_balance_accounts: NonNegativeInt
    oldest_sync_at: datetime | None

class AvailableCashSummary(BaseModel):
    by_currency = list[AvailableCashForCurrency]
    unknown_currency_accounts: NonNegativeInt

