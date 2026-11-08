from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from pydantic import BaseModel, ConfigDict
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.db import get_engine
from app.plaid.router import router as plaid_router


class DatabaseStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")

    connected: bool


class Health(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str
    database: DatabaseStatus


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    yield
    await get_engine().dispose()


app = FastAPI(title="Agentic Finance Companion API", version="0.1.0", lifespan=lifespan)
app.include_router(plaid_router)


@app.get("/api/health", tags=["system"])
async def health() -> Health:
    try:
        async with get_engine().connect() as connection:
            await connection.execute(text("SELECT 1"))
    except (SQLAlchemyError, OSError):
        return Health(status="degraded", database=DatabaseStatus(connected=False))
    return Health(status="ok", database=DatabaseStatus(connected=True))
