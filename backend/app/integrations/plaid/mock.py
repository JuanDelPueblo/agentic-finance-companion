"""In-memory Plaid replacement with fixed synthetic data. Makes no network calls."""

import json
from datetime import UTC, datetime, timedelta

from app import fixtures
from app.integrations.plaid.base import (
    ExchangedItem,
    LinkToken,
    PlaidAccount,
    PlaidError,
    PlaidTransaction,
    PlaidWebhook,
    SyncPage,
)
from app.integrations.plaid.client import parse_webhook

MOCK_PUBLIC_TOKEN_PREFIX = "public-mock-"  # noqa: S105 - not a secret
MOCK_ACCESS_TOKEN_PREFIX = "access-mock-"  # noqa: S105
# Exchanging this public token yields an Item whose calls fail with ITEM_LOGIN_REQUIRED.
BROKEN_PUBLIC_TOKEN = "public-mock-login-required"  # noqa: S105


class MockPlaid:
    name = "mock-plaid"

    def __init__(self, *, page_size: int = 4) -> None:
        self._page_size = page_size

    async def create_link_token(
        self, client_user_id: str, *, access_token: str | None = None
    ) -> LinkToken:
        mode = "update" if access_token else "create"
        return LinkToken(
            link_token=f"link-mock-{mode}-{client_user_id}",
            expiration=datetime.now(UTC) + timedelta(hours=4),
        )

    async def exchange_public_token(self, public_token: str) -> ExchangedItem:
        if not public_token.startswith(MOCK_PUBLIC_TOKEN_PREFIX):
            raise PlaidError(
                "INVALID_INPUT", "INVALID_PUBLIC_TOKEN", "Unknown public token", status_code=400
            )
        suffix = public_token.removeprefix(MOCK_PUBLIC_TOKEN_PREFIX)
        return ExchangedItem(item_id=f"item-mock-{suffix}", access_token=f"access-mock-{suffix}")

    async def get_accounts(self, access_token: str) -> list[PlaidAccount]:
        self._check(access_token)
        return list(fixtures.PLAID_ACCOUNTS)

    async def sync_transactions(self, access_token: str, cursor: str | None) -> SyncPage:
        self._check(access_token)
        offset = int(cursor) if cursor else 0
        all_txns: list[PlaidTransaction] = fixtures.PLAID_TRANSACTIONS
        page = all_txns[offset : offset + self._page_size]
        next_offset = offset + len(page)
        return SyncPage(
            added=page,
            modified=[],
            removed=[],
            next_cursor=str(next_offset),
            has_more=next_offset < len(all_txns),
        )

    async def verify_webhook(self, body: bytes, verification_header: str | None) -> PlaidWebhook:
        return parse_webhook(body)

    def _check(self, access_token: str) -> None:
        if not access_token.startswith(MOCK_ACCESS_TOKEN_PREFIX):
            raise PlaidError("INVALID_INPUT", "INVALID_ACCESS_TOKEN", "Unknown access token")
        if access_token.endswith("login-required"):
            raise PlaidError(
                "ITEM_ERROR",
                "ITEM_LOGIN_REQUIRED",
                "the login details of this item have changed",
                status_code=400,
            )


def mock_webhook_body(webhook_type: str, webhook_code: str, item_id: str) -> bytes:
    """Build a webhook body like Plaid sends, for tests and local experiments."""
    payload = {"webhook_type": webhook_type, "webhook_code": webhook_code, "item_id": item_id}
    return json.dumps(payload).encode()
