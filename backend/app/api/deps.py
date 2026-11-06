from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.integrations.auth import AuthError, AuthProvider, get_auth
from app.schemas.users import Principal

_bearer = HTTPBearer(auto_error=False)


async def current_principal(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    auth: Annotated[AuthProvider, Depends(get_auth)],
) -> Principal:
    try:
        return await auth.authenticate(credentials.credentials if credentials else None)
    except AuthError as exc:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, str(exc), headers={"WWW-Authenticate": "Bearer"}
        ) from exc


CurrentPrincipal = Annotated[Principal, Depends(current_principal)]
