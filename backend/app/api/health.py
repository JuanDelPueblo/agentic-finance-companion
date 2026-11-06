from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import get_session
from app.integrations.auth import get_auth
from app.integrations.llm import get_llm
from app.integrations.plaid import get_plaid
from app.schemas.system import DatabaseStatus, Health, ProviderMode, ProviderStatus

router = APIRouter(tags=["system"])


async def _database_status(session: AsyncSession) -> DatabaseStatus:
    try:
        await session.execute(text("SELECT 1"))
    except (SQLAlchemyError, OSError) as exc:
        return DatabaseStatus(connected=False, error=type(exc).__name__)
    return DatabaseStatus(connected=True)


@router.get("/health")
async def health(session: Annotated[AsyncSession, Depends(get_session)]) -> Health:
    settings = get_settings()
    database = await _database_status(session)
    providers = [
        ProviderStatus(
            name="auth", implementation=get_auth().name, mode=_mode(settings.auth_provider)
        ),
        ProviderStatus(
            name="plaid", implementation=get_plaid().name, mode=_mode(settings.plaid_provider)
        ),
        ProviderStatus(
            name="llm",
            implementation=f"{get_llm().name}:{get_llm().model}",
            mode=_mode(settings.llm_provider),
        ),
    ]
    return Health(
        status="ok" if database.connected else "degraded",
        environment=settings.app_env,
        database=database,
        providers=providers,
    )


def _mode(provider: str) -> ProviderMode:
    return ProviderMode.mock if provider == "mock" else ProviderMode.live
