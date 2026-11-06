"""Authentication boundary: turn a bearer token into a `Principal`."""

from functools import lru_cache

from app.config import get_settings
from app.integrations.auth.base import AuthError, AuthProvider
from app.integrations.auth.mock import MockAuth
from app.integrations.auth.oidc import OIDCAuth

__all__ = ["AuthError", "AuthProvider", "get_auth"]


@lru_cache
def get_auth() -> AuthProvider:
    settings = get_settings()
    if settings.auth_provider == "oidc":
        return OIDCAuth(issuer=settings.oidc_issuer, audience=settings.oidc_audience)
    return MockAuth()
