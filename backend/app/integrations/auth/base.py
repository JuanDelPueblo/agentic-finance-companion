from typing import Protocol

from app.schemas.users import Principal


class AuthError(Exception):
    """The bearer token is missing, malformed, expired, or not issued for this app."""


class AuthProvider(Protocol):
    name: str

    async def authenticate(self, bearer_token: str | None) -> Principal: ...
