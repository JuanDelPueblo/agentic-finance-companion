from enum import StrEnum

from app.schemas.common import Schema


class ProviderMode(StrEnum):
    mock = "mock"
    live = "live"


class ProviderStatus(Schema):
    name: str
    implementation: str
    mode: ProviderMode


class DatabaseStatus(Schema):
    connected: bool
    error: str | None = None


class Health(Schema):
    status: str  # "ok" or "degraded"
    environment: str
    database: DatabaseStatus
    providers: list[ProviderStatus]
