from fastapi import APIRouter

from app.api.deps import CurrentPrincipal
from app.config import get_settings
from app.schemas.users import AuthConfig, Principal

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/config")
async def auth_config() -> AuthConfig:
    """Public settings for starting the OIDC login flow in the browser."""
    s = get_settings()
    if s.auth_provider == "mock":
        return AuthConfig(mode="mock")
    return AuthConfig(
        mode=s.auth_provider,
        issuer=s.oidc_issuer,
        client_id=s.oidc_client_id,
        audience=s.oidc_audience,
    )


@router.get("/me")
async def me(principal: CurrentPrincipal) -> Principal:
    return principal
