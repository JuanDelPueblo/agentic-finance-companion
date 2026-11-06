"""Plaid REST client (https://plaid.com/docs/api/), using httpx directly instead of the SDK."""

import hashlib
import hmac
import json
import time
from datetime import date, datetime
from decimal import Decimal
from typing import Any

import httpx
import jwt

from app.integrations.plaid.base import (
    ExchangedItem,
    LinkToken,
    PlaidAccount,
    PlaidError,
    PlaidTransaction,
    PlaidWebhook,
    SyncPage,
    WebhookVerificationError,
)

PLAID_HOSTS = {
    "sandbox": "https://sandbox.plaid.com",
    "production": "https://production.plaid.com",
}
PLAID_API_VERSION = "2020-09-14"
WEBHOOK_MAX_AGE_SECONDS = 5 * 60


class PlaidClient:
    name = "plaid"

    def __init__(
        self,
        *,
        client_id: str,
        secret: str,
        environment: str = "sandbox",
        webhook_url: str = "",
        client_name: str = "Agentic Finance Companion",
        http: httpx.AsyncClient | None = None,
    ) -> None:
        self._client_id = client_id
        self._secret = secret
        self._webhook_url = webhook_url
        self._client_name = client_name
        self._http = http or httpx.AsyncClient(timeout=30.0)
        self._base_url = PLAID_HOSTS[environment]
        self._webhook_keys: dict[str, dict[str, Any]] = {}

    async def _post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        payload = {"client_id": self._client_id, "secret": self._secret, **body}
        try:
            response = await self._http.post(
                self._base_url + path,
                json=payload,
                headers={"Plaid-Version": PLAID_API_VERSION},
            )
        except httpx.HTTPError as exc:
            raise PlaidError("TRANSPORT_ERROR", type(exc).__name__, str(exc)) from exc
        data: dict[str, Any] = response.json() if response.content else {}
        if response.is_error:
            raise PlaidError(
                data.get("error_type", "API_ERROR"),
                data.get("error_code", f"HTTP_{response.status_code}"),
                data.get("error_message", response.reason_phrase),
                status_code=response.status_code,
                request_id=data.get("request_id"),
            )
        return data

    async def create_link_token(
        self, client_user_id: str, *, access_token: str | None = None
    ) -> LinkToken:
        body: dict[str, Any] = {
            "client_name": self._client_name,
            "language": "en",
            "country_codes": ["US"],
            "user": {"client_user_id": client_user_id},
        }
        if access_token:
            body["access_token"] = access_token  # update mode
        else:
            body["products"] = ["transactions"]
            body["transactions"] = {"days_requested": 730}
        if self._webhook_url:
            body["webhook"] = self._webhook_url
        data = await self._post("/link/token/create", body)
        return LinkToken(
            link_token=data["link_token"], expiration=datetime.fromisoformat(data["expiration"])
        )

    async def exchange_public_token(self, public_token: str) -> ExchangedItem:
        data = await self._post("/item/public_token/exchange", {"public_token": public_token})
        return ExchangedItem(item_id=data["item_id"], access_token=data["access_token"])

    async def get_accounts(self, access_token: str) -> list[PlaidAccount]:
        data = await self._post("/accounts/get", {"access_token": access_token})
        return [_parse_account(a) for a in data["accounts"]]

    async def sync_transactions(self, access_token: str, cursor: str | None) -> SyncPage:
        body: dict[str, Any] = {"access_token": access_token, "count": 500}
        if cursor:
            body["cursor"] = cursor
        data = await self._post("/transactions/sync", body)
        return SyncPage(
            added=[_parse_transaction(t) for t in data["added"]],
            modified=[_parse_transaction(t) for t in data["modified"]],
            removed=[t["transaction_id"] for t in data["removed"]],
            next_cursor=data["next_cursor"],
            has_more=data["has_more"],
        )

    async def create_sandbox_public_token(
        self, institution_id: str = "ins_109508", products: tuple[str, ...] = ("transactions",)
    ) -> str:
        """Sandbox only: create a public token without going through Link (for tests)."""
        data = await self._post(
            "/sandbox/public_token/create",
            {"institution_id": institution_id, "initial_products": list(products)},
        )
        return str(data["public_token"])

    async def verify_webhook(self, body: bytes, verification_header: str | None) -> PlaidWebhook:
        """Verify per https://plaid.com/docs/api/webhooks/webhook-verification/."""
        if not verification_header:
            raise WebhookVerificationError("Missing Plaid-Verification header")
        try:
            header = jwt.get_unverified_header(verification_header)
        except jwt.PyJWTError as exc:
            raise WebhookVerificationError("Malformed verification JWT") from exc
        if header.get("alg") != "ES256" or "kid" not in header:
            raise WebhookVerificationError("Unexpected JWT algorithm or missing key id")

        key = await self._webhook_key(header["kid"])
        try:
            claims = jwt.decode(
                verification_header,
                key=jwt.PyJWK(key).key,
                algorithms=["ES256"],
                options={"require": ["iat", "request_body_sha256"]},
            )
        except jwt.PyJWTError as exc:
            raise WebhookVerificationError(f"Invalid signature: {exc}") from exc
        if time.time() - claims["iat"] > WEBHOOK_MAX_AGE_SECONDS:
            raise WebhookVerificationError("Webhook is too old")
        digest = hashlib.sha256(body).hexdigest()
        if not hmac.compare_digest(digest, claims["request_body_sha256"]):
            raise WebhookVerificationError("Body hash mismatch")
        return parse_webhook(body)

    async def _webhook_key(self, key_id: str) -> dict[str, Any]:
        if key_id not in self._webhook_keys:
            try:
                data = await self._post("/webhook_verification_key/get", {"key_id": key_id})
            except PlaidError as exc:
                raise WebhookVerificationError(f"Cannot fetch verification key: {exc}") from exc
            self._webhook_keys[key_id] = data["key"]
        return self._webhook_keys[key_id]


def parse_webhook(body: bytes) -> PlaidWebhook:
    try:
        raw = json.loads(body)
        return PlaidWebhook(
            webhook_type=raw["webhook_type"],
            webhook_code=raw["webhook_code"],
            item_id=raw.get("item_id"),
            error=raw.get("error"),
            raw=raw,
        )
    except (ValueError, KeyError, TypeError) as exc:
        raise WebhookVerificationError("Malformed webhook body") from exc


def _decimal(value: Any) -> Decimal | None:
    return None if value is None else Decimal(str(value))


def _parse_account(a: dict[str, Any]) -> PlaidAccount:
    balances = a.get("balances") or {}
    return PlaidAccount(
        account_id=a["account_id"],
        name=a.get("official_name") or a["name"],
        type=a["type"],
        subtype=a.get("subtype"),
        current_balance=_decimal(balances.get("current")),
        available_balance=_decimal(balances.get("available")),
        currency=balances.get("iso_currency_code"),
    )


def _parse_transaction(t: dict[str, Any]) -> PlaidTransaction:
    category = (t.get("personal_finance_category") or {}).get("primary")
    authorized = t.get("authorized_date")
    return PlaidTransaction(
        transaction_id=t["transaction_id"],
        account_id=t["account_id"],
        amount=Decimal(str(t["amount"])),
        currency=t.get("iso_currency_code"),
        date=date.fromisoformat(t["date"]),
        authorized_date=date.fromisoformat(authorized) if authorized else None,
        name=t.get("name") or "",
        merchant_name=t.get("merchant_name"),
        category=category,
        pending=bool(t.get("pending")),
        pending_transaction_id=t.get("pending_transaction_id"),
    )
