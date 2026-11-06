"""Plaid integration: account linking, transaction sync, and webhooks."""

from functools import lru_cache

from app.config import get_settings
from app.integrations.plaid.base import (
    PlaidError,
    PlaidProvider,
    PlaidWebhook,
    SyncResult,
    WebhookVerificationError,
    sync_all,
)
from app.integrations.plaid.client import PlaidClient
from app.integrations.plaid.mock import MockPlaid

__all__ = [
    "PlaidError",
    "PlaidProvider",
    "PlaidWebhook",
    "SyncResult",
    "WebhookVerificationError",
    "get_plaid",
    "sync_all",
]


@lru_cache
def get_plaid() -> PlaidProvider:
    settings = get_settings()
    if settings.plaid_provider == "plaid":
        return PlaidClient(
            client_id=settings.plaid_client_id,
            secret=settings.plaid_secret.get_secret_value(),
            environment=settings.plaid_env,
            webhook_url=settings.plaid_webhook_url,
        )
    return MockPlaid()
