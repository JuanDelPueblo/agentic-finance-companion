"""Provider-neutral Plaid interface and data types.

Application code depends on `PlaidProvider` and these types only, never on HTTP
payloads, so the real client and the mock are interchangeable.
"""

import datetime as dt
from decimal import Decimal
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field

# Plaid error codes meaning the user must go through Link (update mode) again.
RELINK_ERROR_CODES = frozenset(
    {
        "ITEM_LOGIN_REQUIRED",
        "PENDING_EXPIRATION",
        "PENDING_DISCONNECT",
        "ACCESS_NOT_GRANTED",
        "INVALID_UPDATED_USERNAME",
        "USER_PERMISSION_REVOKED",
    }
)


class PlaidError(Exception):
    """An error returned by Plaid (or a transport failure talking to it)."""

    def __init__(
        self,
        error_type: str,
        error_code: str,
        message: str,
        *,
        status_code: int | None = None,
        request_id: str | None = None,
    ) -> None:
        super().__init__(f"{error_type}/{error_code}: {message}")
        self.error_type = error_type
        self.error_code = error_code
        self.message = message
        self.status_code = status_code
        self.request_id = request_id

    @property
    def requires_relink(self) -> bool:
        return self.error_code in RELINK_ERROR_CODES


class _Model(BaseModel):
    model_config = ConfigDict(frozen=True)


class LinkToken(_Model):
    link_token: str
    expiration: dt.datetime


class ExchangedItem(_Model):
    item_id: str
    # Secret: store encrypted (app.security), never return to the client or log it.
    access_token: str = Field(repr=False)


class PlaidAccount(_Model):
    account_id: str
    name: str
    type: str
    subtype: str | None
    current_balance: Decimal | None
    available_balance: Decimal | None
    currency: str | None


class PlaidTransaction(_Model):
    transaction_id: str
    account_id: str
    amount: Decimal  # positive = outflow (Plaid convention)
    currency: str | None
    date: dt.date
    authorized_date: dt.date | None
    name: str
    merchant_name: str | None
    category: str | None  # personal_finance_category.primary
    pending: bool
    pending_transaction_id: str | None


class SyncPage(_Model):
    """One page of `/transactions/sync`."""

    added: list[PlaidTransaction]
    modified: list[PlaidTransaction]
    removed: list[str]  # transaction ids
    next_cursor: str
    has_more: bool


class SyncResult(_Model):
    """All pages since `cursor`, merged. Persist the changes and `next_cursor` atomically."""

    added: list[PlaidTransaction]
    modified: list[PlaidTransaction]
    removed: list[str]
    next_cursor: str


class PlaidWebhook(_Model):
    webhook_type: str
    webhook_code: str
    item_id: str | None = None
    error: dict[str, Any] | None = None
    raw: dict[str, Any]

    @property
    def requires_relink(self) -> bool:
        if self.webhook_type == "ITEM" and self.webhook_code in {
            "PENDING_EXPIRATION",
            "PENDING_DISCONNECT",
            "USER_PERMISSION_REVOKED",
        }:
            return True
        return bool(self.error and self.error.get("error_code") in RELINK_ERROR_CODES)

    @property
    def transactions_updated(self) -> bool:
        return self.webhook_type == "TRANSACTIONS" and self.webhook_code == "SYNC_UPDATES_AVAILABLE"


class PlaidProvider(Protocol):
    name: str

    async def create_link_token(
        self, client_user_id: str, *, access_token: str | None = None
    ) -> LinkToken:
        """Create a Link token. Pass `access_token` to open Link in update (re-link) mode."""
        ...

    async def exchange_public_token(self, public_token: str) -> ExchangedItem: ...

    async def get_accounts(self, access_token: str) -> list[PlaidAccount]: ...

    async def sync_transactions(self, access_token: str, cursor: str | None) -> SyncPage: ...

    async def verify_webhook(self, body: bytes, verification_header: str | None) -> PlaidWebhook:
        """Verify the webhook signature and parse it. Raises `WebhookVerificationError`."""
        ...


async def sync_all(provider: PlaidProvider, access_token: str, cursor: str | None) -> SyncResult:
    """Fetch every page since `cursor`, restarting if Plaid reports a mid-pagination mutation."""
    for _attempt in range(3):
        added: list[PlaidTransaction] = []
        modified: list[PlaidTransaction] = []
        removed: list[str] = []
        page_cursor = cursor
        try:
            while True:
                page = await provider.sync_transactions(access_token, page_cursor)
                added += page.added
                modified += page.modified
                removed += page.removed
                page_cursor = page.next_cursor
                if not page.has_more:
                    return SyncResult(
                        added=added, modified=modified, removed=removed, next_cursor=page_cursor
                    )
        except PlaidError as exc:
            if exc.error_code != "TRANSACTIONS_SYNC_MUTATION_DURING_PAGINATION":
                raise
    raise PlaidError(
        "TRANSACTIONS_ERROR",
        "TRANSACTIONS_SYNC_MUTATION_DURING_PAGINATION",
        "Sync kept changing during pagination; try again later",
    )


class WebhookVerificationError(Exception):
    pass
