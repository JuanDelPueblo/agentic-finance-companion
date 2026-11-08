from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import User

# The local test user that every request acts as until real sign-in exists.
LOCAL_TEST_USER_ID = UUID("166bb3fb-dc61-4786-b5b5-7d049c7f927a")
LOCAL_TEST_AUTH_SUBJECT = "local:plaid-sandbox"

bearer = HTTPBearer()


async def get_current_user_id(
    session: Annotated[AsyncSession, Depends(get_session)],
    auth: Annotated[HTTPAuthorizationCredentials, Depends(bearer)],
) -> UUID:

    # TODO: validate auth.credentials and look up the real user.
    # For now every request acts as the local test user.

    user = await session.get(User, LOCAL_TEST_USER_ID)
    if user is None:
        user = User(
            user_id=LOCAL_TEST_USER_ID,
            auth_subject=LOCAL_TEST_AUTH_SUBJECT,
            email="sandbox@example.com",
            display_name="Local test user",
        )
        session.add(user)
        await session.commit()
    elif user.auth_subject != LOCAL_TEST_AUTH_SUBJECT:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Another user already has the local test user's ID"
        )

    return user.user_id
