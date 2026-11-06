import hashlib
import json
import time
from collections.abc import Iterator
from decimal import Decimal
from typing import Any

import httpx
import jwt
import pytest
import respx
from cryptography.hazmat.primitives.asymmetric import ec

from app.integrations.plaid import PlaidError, WebhookVerificationError, sync_all
from app.integrations.plaid.base import SyncPage
from app.integrations.plaid.client import PlaidClient
from app.integrations.plaid.mock import BROKEN_PUBLIC_TOKEN, MockPlaid, mock_webhook_body

BASE = "https://sandbox.plaid.com"


def _client() -> PlaidClient:
    return PlaidClient(client_id="cid", secret="sec", http=httpx.AsyncClient())


# --- mock provider -------------------------------------------------------------------------


async def test_mock_link_exchange_and_sync_all_pages() -> None:
    plaid = MockPlaid(page_size=3)
    item = await plaid.exchange_public_token("public-mock-abc")
    assert len(await plaid.get_accounts(item.access_token)) == 3

    result = await sync_all(plaid, item.access_token, cursor=None)
    assert len(result.added) == 10
    assert len({t.transaction_id for t in result.added}) == 10  # no duplicates across pages

    again = await sync_all(plaid, item.access_token, cursor=result.next_cursor)
    assert again.added == []  # resuming from the stored cursor is idempotent


async def test_mock_broken_item_requires_relink() -> None:
    plaid = MockPlaid()
    item = await plaid.exchange_public_token(BROKEN_PUBLIC_TOKEN)
    with pytest.raises(PlaidError) as excinfo:
        await plaid.get_accounts(item.access_token)
    assert excinfo.value.requires_relink


# --- real client against a mocked HTTP layer -----------------------------------------------


@respx.mock
async def test_link_token_request_shape() -> None:
    route = respx.post(f"{BASE}/link/token/create").respond(
        json={"link_token": "link-sandbox-1", "expiration": "2026-11-06T20:00:00Z"}
    )
    token = await _client().create_link_token("user-1")
    body = json.loads(route.calls.last.request.content)
    assert body["client_id"] == "cid" and body["secret"] == "sec"
    assert body["products"] == ["transactions"]
    assert route.calls.last.request.headers["Plaid-Version"] == "2020-09-14"
    assert token.link_token == "link-sandbox-1"


@respx.mock
async def test_plaid_errors_are_typed() -> None:
    respx.post(f"{BASE}/accounts/get").respond(
        400,
        json={
            "error_type": "ITEM_ERROR",
            "error_code": "ITEM_LOGIN_REQUIRED",
            "error_message": "login required",
            "request_id": "req-1",
        },
    )
    with pytest.raises(PlaidError) as excinfo:
        await _client().get_accounts("access-sandbox-1")
    assert excinfo.value.requires_relink
    assert excinfo.value.request_id == "req-1"


@respx.mock
async def test_sync_parses_transactions() -> None:
    respx.post(f"{BASE}/transactions/sync").respond(
        json={
            "added": [
                {
                    "transaction_id": "t1",
                    "account_id": "a1",
                    "amount": 12.5,
                    "iso_currency_code": "USD",
                    "date": "2026-10-01",
                    "authorized_date": None,
                    "name": "Coffee",
                    "merchant_name": "Bean There",
                    "personal_finance_category": {"primary": "FOOD_AND_DRINK"},
                    "pending": True,
                    "pending_transaction_id": None,
                }
            ],
            "modified": [],
            "removed": [{"transaction_id": "t0"}],
            "next_cursor": "c1",
            "has_more": False,
        }
    )
    page = await _client().sync_transactions("access-sandbox-1", cursor=None)
    assert page.added[0].amount == Decimal("12.5")
    assert page.added[0].category == "FOOD_AND_DRINK"
    assert page.removed == ["t0"]


async def test_sync_all_restarts_after_mutation_during_pagination() -> None:
    calls: list[str | None] = []

    class Flaky(MockPlaid):
        async def sync_transactions(self, access_token: str, cursor: str | None) -> SyncPage:
            calls.append(cursor)
            if len(calls) == 2:
                raise PlaidError(
                    "TRANSACTIONS_ERROR", "TRANSACTIONS_SYNC_MUTATION_DURING_PAGINATION", "retry"
                )
            return await super().sync_transactions(access_token, cursor)

    result = await sync_all(Flaky(page_size=6), "access-mock-x", cursor=None)
    assert calls[:3] == [None, "6", None]  # restarted from the original cursor
    assert len(result.added) == 10


# --- webhook verification ------------------------------------------------------------------


@pytest.fixture
def webhook_key() -> ec.EllipticCurvePrivateKey:
    return ec.generate_private_key(ec.SECP256R1())


def _signed(key: ec.EllipticCurvePrivateKey, body: bytes, **overrides: Any) -> str:
    claims = {"iat": int(time.time()), "request_body_sha256": hashlib.sha256(body).hexdigest()}
    return jwt.encode(claims | overrides, key, algorithm="ES256", headers={"kid": "k1"})


@pytest.fixture
def key_endpoint(webhook_key: ec.EllipticCurvePrivateKey) -> Iterator[respx.MockRouter]:
    jwk: dict[str, Any] = jwt.algorithms.ECAlgorithm.to_jwk(webhook_key.public_key(), as_dict=True)
    with respx.mock as router:
        router.post(f"{BASE}/webhook_verification_key/get").respond(json={"key": jwk})
        yield router


async def test_webhook_valid(
    key_endpoint: respx.MockRouter, webhook_key: ec.EllipticCurvePrivateKey
) -> None:
    body = mock_webhook_body("TRANSACTIONS", "SYNC_UPDATES_AVAILABLE", "item-1")
    webhook = await _client().verify_webhook(body, _signed(webhook_key, body))
    assert webhook.transactions_updated and webhook.item_id == "item-1"


async def test_webhook_rejects_tampered_body(
    key_endpoint: respx.MockRouter, webhook_key: ec.EllipticCurvePrivateKey
) -> None:
    body = mock_webhook_body("ITEM", "ERROR", "item-1")
    header = _signed(webhook_key, body)
    with pytest.raises(WebhookVerificationError, match="hash"):
        await _client().verify_webhook(body.replace(b"item-1", b"item-2"), header)


async def test_webhook_rejects_stale_and_missing(
    key_endpoint: respx.MockRouter, webhook_key: ec.EllipticCurvePrivateKey
) -> None:
    body = mock_webhook_body("ITEM", "ERROR", "item-1")
    with pytest.raises(WebhookVerificationError, match="too old"):
        await _client().verify_webhook(body, _signed(webhook_key, body, iat=int(time.time()) - 600))
    with pytest.raises(WebhookVerificationError, match="Missing"):
        await _client().verify_webhook(body, None)


# --- API ------------------------------------------------------------------------------------


async def test_api_link_and_exchange(client: httpx.AsyncClient) -> None:
    link = await client.post("/api/plaid/link-token")
    assert link.status_code == 200 and link.json()["link_token"].startswith("link-mock-")

    linked = await client.post("/api/plaid/exchange", json={"public_token": "public-mock-1"})
    assert linked.status_code == 200
    assert "access_token" not in linked.text
    assert len(linked.json()["accounts"]) == 3


async def test_api_relink_error_is_409(client: httpx.AsyncClient) -> None:
    response = await client.post("/api/plaid/exchange", json={"public_token": BROKEN_PUBLIC_TOKEN})
    assert response.status_code == 409
    assert response.json() == {
        "detail": "the login details of this item have changed",
        "code": "ITEM_LOGIN_REQUIRED",
        "requires_relink": True,
    }


async def test_api_webhook(client: httpx.AsyncClient) -> None:
    body = mock_webhook_body("TRANSACTIONS", "SYNC_UPDATES_AVAILABLE", "item-1")
    assert (await client.post("/api/plaid/webhook", content=body)).status_code == 202
    assert (await client.post("/api/plaid/webhook", content=b"not json")).status_code == 400
