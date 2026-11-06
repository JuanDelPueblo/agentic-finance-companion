import time
from collections.abc import Iterator
from typing import Any

import httpx
import jwt
import pytest
import respx
from cryptography.hazmat.primitives.asymmetric import rsa

from app.integrations.auth.base import AuthError
from app.integrations.auth.mock import MockAuth
from app.integrations.auth.oidc import OIDCAuth

ISSUER = "https://id.example.test"
AUDIENCE = "finance-api"


async def test_mock_auth_default_and_named_users() -> None:
    auth = MockAuth()
    assert (await auth.authenticate(None)).subject == "dev-user"
    assert (await auth.authenticate("dev:alice")).subject == "alice"
    with pytest.raises(AuthError):
        await auth.authenticate("not-a-dev-token")


@pytest.fixture
def signing_key() -> rsa.RSAPrivateKey:
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture
def idp(signing_key: rsa.RSAPrivateKey) -> Iterator[respx.MockRouter]:
    jwk: dict[str, Any] = jwt.algorithms.RSAAlgorithm.to_jwk(signing_key.public_key(), as_dict=True)
    jwk |= {"kid": "key-1", "use": "sig", "alg": "RS256"}
    with respx.mock(assert_all_called=False) as router:
        router.get(f"{ISSUER}/.well-known/openid-configuration").respond(
            json={"issuer": ISSUER, "jwks_uri": f"{ISSUER}/jwks"}
        )
        router.get(f"{ISSUER}/jwks").respond(json={"keys": [jwk]})
        yield router


def _token(key: rsa.RSAPrivateKey, **overrides: Any) -> str:
    now = int(time.time())
    claims = {"iss": ISSUER, "aud": AUDIENCE, "sub": "user-123", "iat": now, "exp": now + 300}
    return jwt.encode(claims | overrides, key, algorithm="RS256", headers={"kid": "key-1"})


async def test_oidc_accepts_valid_token(
    idp: respx.MockRouter, signing_key: rsa.RSAPrivateKey
) -> None:
    auth = OIDCAuth(issuer=ISSUER, audience=AUDIENCE, http=httpx.AsyncClient())
    principal = await auth.authenticate(_token(signing_key, email="u@example.test"))
    assert principal.subject == "user-123"
    assert principal.email == "u@example.test"


@pytest.mark.parametrize(
    "overrides",
    [{"aud": "someone-else"}, {"iss": "https://evil.test"}, {"exp": int(time.time()) - 10}],
    ids=["wrong-audience", "wrong-issuer", "expired"],
)
async def test_oidc_rejects_bad_claims(
    idp: respx.MockRouter, signing_key: rsa.RSAPrivateKey, overrides: dict[str, Any]
) -> None:
    auth = OIDCAuth(issuer=ISSUER, audience=AUDIENCE, http=httpx.AsyncClient())
    with pytest.raises(AuthError):
        await auth.authenticate(_token(signing_key, **overrides))


async def test_oidc_rejects_foreign_signature(idp: respx.MockRouter) -> None:
    other = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    auth = OIDCAuth(issuer=ISSUER, audience=AUDIENCE, http=httpx.AsyncClient())
    with pytest.raises(AuthError):
        await auth.authenticate(_token(other))


async def test_api_rejects_invalid_token(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/auth/me", headers={"Authorization": "Bearer nope"})
    assert response.status_code == 401
    ok = await client.get("/api/auth/me", headers={"Authorization": "Bearer dev:alice"})
    assert ok.json()["subject"] == "alice"
