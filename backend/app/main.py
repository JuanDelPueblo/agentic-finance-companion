from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api import auth, finance, health, plaid
from app.config import get_settings
from app.db import get_engine
from app.integrations.plaid import PlaidError


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    get_settings()  # fail at startup, not on the first request, if settings are invalid
    yield
    await get_engine().dispose()


async def plaid_error_handler(_request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, PlaidError)
    return JSONResponse(
        status_code=409 if exc.requires_relink else 502,
        content={
            "detail": exc.message,
            "code": exc.error_code,
            "requires_relink": exc.requires_relink,
        },
    )


def create_app() -> FastAPI:
    app = FastAPI(title="Agentic Finance Companion API", version="0.1.0", lifespan=lifespan)
    for module in (health, auth, plaid, finance):
        app.include_router(module.router, prefix="/api")
    app.add_exception_handler(PlaidError, plaid_error_handler)
    return app


app = create_app()
