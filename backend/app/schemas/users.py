from app.schemas.common import Schema


class Principal(Schema):
    """The authenticated caller, as asserted by the identity provider."""

    subject: str
    email: str | None = None
    name: str | None = None
    provider: str


class AuthConfig(Schema):
    """Public settings the frontend needs to start an OIDC login."""

    mode: str
    issuer: str | None = None
    client_id: str | None = None
    audience: str | None = None
