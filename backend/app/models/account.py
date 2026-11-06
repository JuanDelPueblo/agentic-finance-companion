from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import CHAR, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.plaid_item import PlaidItem
    from app.models.transaction import Transaction


class Account(Base):
    __tablename__ = "accounts"

    account_id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    item_id: Mapped[UUID] = mapped_column(ForeignKey("plaid_items.item_id"))
    plaid_account_ref: Mapped[str] = mapped_column(String(128))
    name: Mapped[str] = mapped_column(String(120))
    account_type: Mapped[str] = mapped_column(String(30))
    account_subtype: Mapped[str | None] = mapped_column(String(30))
    current_balance: Mapped[Decimal | None] = mapped_column(Numeric)
    available_balance: Mapped[Decimal | None] = mapped_column(Numeric)
    currency_code: Mapped[str | None] = mapped_column(CHAR(3))

    item: Mapped[PlaidItem] = relationship(back_populates="accounts")
    transactions: Mapped[list[Transaction]] = relationship(back_populates="account")
