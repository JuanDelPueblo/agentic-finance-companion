"""Opt-in checks against the real Plaid Sandbox. Skipped unless credentials are set."""

import os

import httpx
import pytest

from app.integrations.plaid import sync_all
from app.integrations.plaid.client import PlaidClient

pytestmark = [
    pytest.mark.plaid_sandbox,
    pytest.mark.skipif(
        not (os.getenv("PLAID_CLIENT_ID") and os.getenv("PLAID_SECRET")),
        reason="PLAID_CLIENT_ID / PLAID_SECRET not set",
    ),
]


async def test_sandbox_link_exchange_and_sync() -> None:
    plaid = PlaidClient(
        client_id=os.environ["PLAID_CLIENT_ID"],
        secret=os.environ["PLAID_SECRET"],
        http=httpx.AsyncClient(timeout=60),
    )
    public_token = await plaid.create_sandbox_public_token()
    item = await plaid.exchange_public_token(public_token)
    assert await plaid.get_accounts(item.access_token)
    result = await sync_all(plaid, item.access_token, cursor=None)
    assert result.next_cursor  # new Items may report zero transactions until Plaid finishes
