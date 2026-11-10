from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from jose import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session, get_settings
from app.core.security import create_access_token
from app.main import app
from app.models import User

pytestmark = pytest.mark.anyio


@pytest.fixture
async def client(
    session: AsyncSession, database_url: str, monkeypatch: pytest.MonkeyPatch
) -> AsyncIterator[AsyncClient]:
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("SECRET_KEY", "auth-test-secret-with-more-than-32-characters")
    get_settings.cache_clear()
    app.dependency_overrides[get_session] = lambda: session
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
            yield http
    finally:
        app.dependency_overrides.pop(get_session, None)
        get_settings.cache_clear()


async def test_register_login_and_me(client: AsyncClient, session: AsyncSession) -> None:
    registration = await client.post(
        "/api/auth/register",
        json={
            "email": "Ada@Example.com",
            "password": "correct-horse-battery-staple",
            "display_name": "Ada",
        },
    )
    assert registration.status_code == 201
    user = registration.json()
    assert user["email"] == "ada@example.com"
    assert user["display_name"] == "Ada"
    assert "password" not in user
    assert "hashed_password" not in user
    stored = await session.scalar(select(User).where(User.email == "ada@example.com"))
    assert stored.hashed_password != "correct-horse-battery-staple"
    assert stored.hashed_password.startswith("$argon2")

    duplicate = await client.post(
        "/api/auth/register",
        json={"email": "ADA@example.com", "password": "another-password"},
    )
    assert duplicate.status_code == 409

    login = await client.post(
        "/api/auth/login",
        data={"username": "ADA@example.com", "password": "correct-horse-battery-staple"},
    )
    assert login.status_code == 200
    assert login.json()["token_type"] == "bearer"
    token = login.json()["access_token"]
    assert jwt.get_unverified_claims(token)["sub"] == "ada@example.com"

    profile = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert profile.status_code == 200
    assert profile.json() == user

    wrong_password = await client.post(
        "/api/auth/login",
        data={"username": "ada@example.com", "password": "wrong-password"},
    )
    assert wrong_password.status_code == 401
    assert (await client.get("/api/auth/me")).status_code == 401


async def test_invalid_expired_and_unknown_user_tokens(client: AsyncClient) -> None:
    settings = get_settings()
    secret = settings.secret_key.get_secret_value()
    expired = jwt.encode(
        {"sub": "missing@example.com", "exp": datetime.now(UTC) - timedelta(minutes=1)},
        secret,
        algorithm=settings.algorithm,
    )
    missing_expiry = jwt.encode(
        {"sub": "missing@example.com"}, secret, algorithm=settings.algorithm
    )
    unknown_user = create_access_token("missing@example.com")
    for token in (expired, missing_expiry, unknown_user, "invalid.token.value"):
        response = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 401


async def test_registration_rejects_invalid_input(client: AsyncClient) -> None:
    response = await client.post(
        "/api/auth/register", json={"email": "not-an-email", "password": "short"}
    )
    assert response.status_code == 422
