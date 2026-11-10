from datetime import UTC, datetime, timedelta

from jose import JWTError, jwt
from pwdlib import PasswordHash

from app.core.db import get_settings

password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return password_hash.verify(plain, hashed)


def _token_settings() -> tuple[str, str, int]:
    settings = get_settings()
    secret = settings.secret_key.get_secret_value() if settings.secret_key else ""
    if len(secret) < 32:
        raise RuntimeError("SECRET_KEY must contain at least 32 characters")
    return secret, settings.algorithm, settings.access_token_expire_min


def create_access_token(subject: str, expires_minutes: int | None = None) -> str:
    secret, algorithm, default_minutes = _token_settings()
    minutes = default_minutes if expires_minutes is None else expires_minutes
    if minutes <= 0:
        raise ValueError("Token lifetime must be positive")
    expires_at = datetime.now(UTC) + timedelta(minutes=minutes)
    return jwt.encode({"sub": subject, "exp": expires_at}, secret, algorithm=algorithm)


def decode_access_token(token: str) -> str | None:
    secret, algorithm, _ = _token_settings()
    try:
        payload = jwt.decode(token, secret, algorithms=[algorithm])
    except JWTError:
        return None
    subject = payload.get("sub")
    if "exp" not in payload or not isinstance(subject, str) or not subject:
        return None
    return subject
