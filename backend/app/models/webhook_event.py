from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.job import Job
    from app.models.plaid_item import PlaidItem


class WebhookEvent(Base):
    __tablename__ = "webhook_events"

    event_id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    item_id: Mapped[UUID] = mapped_column(ForeignKey("plaid_items.item_id"))
    webhook_type: Mapped[str] = mapped_column(String(40))
    webhook_code: Mapped[str] = mapped_column(String(60))
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    item: Mapped[PlaidItem] = relationship(back_populates="webhook_events")
    jobs: Mapped[list[Job]] = relationship(back_populates="webhook_event")
