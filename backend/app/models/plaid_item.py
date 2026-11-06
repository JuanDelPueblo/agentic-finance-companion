from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.account import Account
    from app.models.user import User
    from app.models.webhook_event import WebhookEvent


class PlaidItem(Base):
    __tablename__ = "plaid_items"

    item_id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.user_id"))
    plaid_item_ref: Mapped[str] = mapped_column(String(128))
    access_token_encrypted: Mapped[str] = mapped_column(Text)
    institution_name: Mapped[str | None] = mapped_column(String(120))
    connection_status: Mapped[str] = mapped_column(String(30))
    sync_cursor: Mapped[str | None] = mapped_column(Text)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship(back_populates="plaid_items")
    accounts: Mapped[list[Account]] = relationship(back_populates="item")
    webhook_events: Mapped[list[WebhookEvent]] = relationship(back_populates="item")
