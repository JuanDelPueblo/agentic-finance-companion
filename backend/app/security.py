"""Encryption for credentials stored at rest (e.g. Plaid access tokens)."""

from cryptography.fernet import Fernet, InvalidToken

from app.config import get_settings


class TokenEncryptionError(RuntimeError):
    pass


def _fernet() -> Fernet:
    key = get_settings().token_encryption_key.get_secret_value()
    if not key:
        raise TokenEncryptionError("TOKEN_ENCRYPTION_KEY is not set")
    return Fernet(key)


def encrypt_token(plaintext: str) -> str:
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt_token(ciphertext: str) -> str:
    try:
        return _fernet().decrypt(ciphertext.encode()).decode()
    except InvalidToken as exc:
        raise TokenEncryptionError("Stored token cannot be decrypted with the current key") from exc
