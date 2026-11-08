"""Shared fixtures for tests that need a real PostgreSQL database.

Database tests run only when TEST_DATABASE_URL is set; otherwise they are skipped, or they
fail if REQUIRE_TEST_DATABASE is set (CI sets it). The database name must end in "_test",
because the test run drops and recreates its schema.
"""

import os
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import create_engine, make_url, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from alembic import command

BACKEND_DIR = Path(__file__).resolve().parent.parent


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(scope="session")
def database_url() -> str:
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        if os.environ.get("REQUIRE_TEST_DATABASE"):
            pytest.fail("REQUIRE_TEST_DATABASE is set, but TEST_DATABASE_URL is not")
        pytest.skip("TEST_DATABASE_URL is not set")
    database = make_url(url).database or ""
    if not database.endswith("_test"):
        pytest.fail(f"TEST_DATABASE_URL must name a database ending in _test, not {database!r}")

    # Start from an empty schema and apply every migration, so the tests also check them.
    engine = create_engine(url, poolclass=NullPool)
    with engine.begin() as connection:
        connection.execute(text("DROP SCHEMA public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))
    engine.dispose()

    previous = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = url  # alembic/env.py reads it through Settings
    try:
        command.upgrade(Config(str(BACKEND_DIR / "alembic.ini")), "head")
    finally:
        if previous is None:
            del os.environ["DATABASE_URL"]
        else:
            os.environ["DATABASE_URL"] = previous
    return url


@pytest.fixture
async def session(database_url: str) -> AsyncIterator[AsyncSession]:
    """A session whose changes, including commits, are rolled back after the test."""
    engine = create_async_engine(database_url, poolclass=NullPool)
    async with engine.connect() as connection:
        transaction = await connection.begin()
        async with AsyncSession(
            bind=connection,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        ) as session:
            yield session
        await transaction.rollback()
    await engine.dispose()
