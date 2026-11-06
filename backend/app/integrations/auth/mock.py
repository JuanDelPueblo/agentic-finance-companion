"""Development-only authentication. Refused at startup when APP_ENV=production.

- No token: you are the default demo user.
- `Authorization: Bearer dev:<subject>`: you are `<subject>` (to test per-user access).
"""

from app.integrations.auth.base import AuthError
from app.schemas.users import Principal

DEFAULT_SUBJECT = "dev-user"


class MockAuth:
    name = "mock"

    async def authenticate(self, bearer_token: str | None) -> Principal:
        subject = DEFAULT_SUBJECT
        if bearer_token:
            if not bearer_token.startswith("dev:") or len(bearer_token) == 4:
                raise AuthError("Mock auth expects 'dev:<subject>' tokens")
            subject = bearer_token.removeprefix("dev:")
        return Principal(
            subject=subject,
            email=f"{subject}@example.test",
            name=subject.replace("-", " ").title(),
            provider=self.name,
        )
