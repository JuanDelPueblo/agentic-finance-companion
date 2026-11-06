from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.chat_message import ChatMessage
    from app.models.financial_state import FinancialState
    from app.models.plan_validation import PlanValidation
    from app.models.user import User


class Plan(Base):
    __tablename__ = "plans"

    plan_id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.user_id"))
    state_id: Mapped[UUID] = mapped_column(ForeignKey("financial_states.state_id"))
    trigger_reason: Mapped[str] = mapped_column(String(60))
    plan_body: Mapped[Any] = mapped_column(JSONB, nullable=False)
    model_name: Mapped[str] = mapped_column(String(60))
    status: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped[User] = relationship(back_populates="plans")
    state: Mapped[FinancialState] = relationship(back_populates="plans")
    validations: Mapped[list[PlanValidation]] = relationship(back_populates="plan")
    chat_messages: Mapped[list[ChatMessage]] = relationship(back_populates="plan")
