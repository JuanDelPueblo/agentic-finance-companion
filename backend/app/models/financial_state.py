from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from sqlalchemy import CHAR, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.plan import Plan
    from app.models.user import User


class FinancialState(Base):
    __tablename__ = "financial_states"

    state_id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.user_id"))
    input_hash: Mapped[str] = mapped_column(CHAR(64))
    engine_version: Mapped[str] = mapped_column(String(20))
    state_snapshot: Mapped[Any] = mapped_column(JSONB, nullable=False)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    user: Mapped[User] = relationship(back_populates="financial_states")
    plans: Mapped[list[Plan]] = relationship(back_populates="state")
