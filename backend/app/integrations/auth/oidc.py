"""Validate OAuth 2.0 / OIDC access tokens (JWTs) issued by an external identity provider.

The frontend runs the login flow (authorization code + PKCE) against the provider and
sends the access token as `Authorization: Bearer <jwt>`. The backend keeps no sessions.
"""

import time
from typing import Any

import httpx
import jwt

from app.integrations.auth.base import AuthError
from app.schemas.users import Principal

ALLOWED_ALGORITHMS = ["RS256", "ES256"]
JWKS_CACHE_SECONDS = 3600


class OIDCAuth:
    name = "oidc"

    def __init__(
        self, *, issuer: str, audience: str, http: httpx.AsyncClient | None = None
    ) -> None:
        self._issuer = issuer.rstrip("/")
        self._audience = audience
        self._http = http or httpx.AsyncClient(timeout=10.0)
        self._jwks: jwt.PyJWKSet | None = None
        self._jwks_fetched_at = 0.0

    async def authenticate(self, bearer_token: str | None) -> Principal:
        if not bearer_token:
            raise AuthError("Missing bearer token")
        try:
            kid = jwt.get_unverified_header(bearer_token).get("kid")
            key = await self._signing_key(kid)
            claims: dict[str, Any] = jwt.decode(
                bearer_token,
                key=key.key,
                algorithms=ALLOWED_ALGORITHMS,
                audience=self._audience,
                issuer=self._issuer_claim(),
                options={"require": ["exp", "iat", "sub"]},
            )
        except jwt.PyJWTError as exc:
            raise AuthError(f"Invalid token: {exc}") from exc
        return Principal(
            subject=claims["sub"],
            email=claims.get("email"),
            name=claims.get("name"),
            provider=self.name,
        )

    def _issuer_claim(self) -> list[str]:
        # Providers differ on whether `iss` carries a trailing slash.
        return [self._issuer, self._issuer + "/"]

    async def _signing_key(self, kid: str | None) -> jwt.PyJWK:
        if self._jwks is None or time.monotonic() - self._jwks_fetched_at > JWKS_CACHE_SECONDS:
            await self._refresh_jwks()
        assert self._jwks is not None
        for key in self._jwks.keys:
            if key.key_id == kid:
                return key
        await self._refresh_jwks()  # the provider may have rotated keys
        for key in self._jwks.keys:
            if key.key_id == kid:
                return key
        raise AuthError("Token signed with an unknown key")

    async def _refresh_jwks(self) -> None:
        try:
            discovery = await self._http.get(f"{self._issuer}/.well-known/openid-configuration")
            discovery.raise_for_status()
            jwks = await self._http.get(discovery.json()["jwks_uri"])
            jwks.raise_for_status()
            self._jwks = jwt.PyJWKSet.from_dict(jwks.json())
        except (httpx.HTTPError, KeyError, ValueError, jwt.PyJWTError) as exc:
            raise AuthError(f"Cannot load identity provider keys: {exc}") from exc
        self._jwks_fetched_at = time.monotonic()
