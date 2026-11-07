import os
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import User

# For local testing
LOCAL_TEST_USER_ID = UUID("166bb3fb-dc61-4786-b5b5-7d049c7f927a")
LOCAL_TEST_AUTH_SUBJECT = "local:plaid-sandbox"

async def get_current_user_id(
        request: Request, 
        session: AsyncSession = Depends(get_session),
    ) -> UUID:

    user = await session.get(User, LOCAL_TEST_USER_ID)
    if user is None or user.auth_subject != LOCAL_TEST_AUTH_SUBJECT:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Local Plaid test user is not seeded",
        )

    return user.user_id