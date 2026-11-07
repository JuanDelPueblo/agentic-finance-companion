from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.chat_message import ChatMessage
    from app.models.financial_state import FinancialState
    from app.models.goal import Goal
    from app.models.plaid_item import PlaidItem
    from app.models.plan import Plan
    from app.models.user_context import UserContext


class User(Base):
    __tablename__ = "users"

    user_id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    auth_subject: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str] = mapped_column(String(255))
    display_name: Mapped[str | None] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    plaid_items: Mapped[list[PlaidItem]] = relationship(back_populates="user")
    context_entries: Mapped[list[UserContext]] = relationship(back_populates="user")
    goals: Mapped[list[Goal]] = relationship(back_populates="user")
    financial_states: Mapped[list[FinancialState]] = relationship(back_populates="user")
    plans: Mapped[list[Plan]] = relationship(back_populates="user")
    chat_messages: Mapped[list[ChatMessage]] = relationship(back_populates="user")
