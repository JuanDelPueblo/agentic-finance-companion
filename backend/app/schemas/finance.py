"""Accounts, transactions, and Plaid account linking."""

from datetime import date, datetime
from enum import StrEnum
from uuid import UUID

from app.schemas.common import CurrencyCode, Money, Schema


class ConnectionStatus(StrEnum):
    healthy = "healthy"
    relink_required = "relink_required"  # e.g. ITEM_LOGIN_REQUIRED, expired consent
    error = "error"


class TransactionState(StrEnum):
    pending = "pending"
    posted = "posted"
    removed = "removed"


class Account(Schema):
    id: UUID
    name: str
    type: str  # Plaid account type, e.g. "depository", "credit"
    subtype: str | None
    current_balance: Money | None
    available_balance: Money | None
    currency: CurrencyCode
    connection_status: ConnectionStatus
    last_synced_at: datetime | None


class Transaction(Schema):
    id: UUID
    account_id: UUID
    # Plaid convention: positive = money leaving the account, negative = money coming in.
    amount: Money
    currency: CurrencyCode
    date: date
    merchant_name: str | None
    category: str | None
    state: TransactionState


class LinkTokenResponse(Schema):
    link_token: str
    expiration: datetime


class PublicTokenExchange(Schema):
    public_token: str


class LinkedAccount(Schema):
    name: str
    type: str
    subtype: str | None


class LinkedItem(Schema):
    """Result of connecting an institution. The access token never leaves the server."""

    item_id: str
    accounts: list[LinkedAccount]
