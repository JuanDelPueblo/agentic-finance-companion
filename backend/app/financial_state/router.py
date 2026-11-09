from datetime import UTC, date, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.dependencies import get_current_user_id

from app.financial_state.engine import (get_available_cash, 
                                        get_monthly_income,
                                        get_credit_balance_owed)
from app.financial_state.schemas import (AvailableCashSummary, 
                                         MonthlyAmountSummary, 
                                         CreditBalanceOwedSummary)

router = APIRouter(prefix="/api/financial-state", tags=["financial-state"])

CurrentUserId = Annotated[UUID, Depends(get_current_user_id)]
Session = Annotated[AsyncSession, Depends(get_session)]


@router.get("/available-cash")
async def available_cash(user_id: CurrentUserId, session: Session) -> AvailableCashSummary:
    return await get_available_cash(session, user_id)


@router.get("/monthly-income")
async def monthly_income(user_id: CurrentUserId, session: Session, month: date | None) -> MonthlyAmountSummary:
    return await get_monthly_income(session, user_id, month or datetime.now(UTC).date())

@router.get("/credit-balance-owned")
async def credit_balance_owned(session: Session, user_id: CurrentUserId) -> CreditBalanceOwedSummary:
    return await get_credit_balance_owed