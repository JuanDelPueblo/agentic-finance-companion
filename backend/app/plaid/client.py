import asyncio
import json
from collections.abc import Callable
from functools import lru_cache
from typing import Any

import plaid
from cryptography.fernet import Fernet
from fastapi import HTTPException
from plaid.api.plaid_api import PlaidApi

from app.core.db import Settings


class PlaidError(HTTPException):
    def __init__(self, error_type: str, code: str, message: str) -> None:
        if code == "ITEM_LOGIN_REQUIRED":
            status_code = 409  # The user must reconnect the bank through Plaid Link.
        elif error_type in ("INVALID_INPUT", "INVALID_REQUEST"):
            status_code = 400
        else:
            status_code = 502
        super().__init__(status_code, message)
        self.code = code


@lru_cache
def get_plaid() -> PlaidApi:
    settings = Settings()
    if not settings.plaid_client_id or not settings.plaid_sandbox_secret:
        raise RuntimeError("Set PLAID_CLIENT_ID and PLAID_SANDBOX_SECRET in .env")
    configuration = plaid.Configuration(
        host=plaid.Environment.Sandbox,
        api_key={
            "clientId": settings.plaid_client_id,
            "secret": settings.plaid_sandbox_secret.get_secret_value(),
        },
    )
    return PlaidApi(plaid.ApiClient(configuration))


async def call(method: Callable[[Any], Any], request: Any) -> Any:
    """Run a Plaid SDK method in a thread, since the SDK blocks, and raise PlaidError on failure."""
    try:
        return await asyncio.to_thread(method, request)
    except plaid.ApiException as error:
        body = json.loads(error.body or "{}")
        raise PlaidError(
            body.get("error_type", ""), body.get("error_code", ""), body.get("error_message", "")
        ) from error


# The project proposal requires Plaid access tokens to be encrypted at rest.
def _fernet() -> Fernet:
    key = Settings().token_encryption_key
    if not key:
        raise RuntimeError("Set TOKEN_ENCRYPTION_KEY in .env")
    return Fernet(key.get_secret_value())


def encrypt_token(token: str) -> str:
    return _fernet().encrypt(token.encode()).decode()


def decrypt_token(token: str) -> str:
    return _fernet().decrypt(token.encode()).decode()
