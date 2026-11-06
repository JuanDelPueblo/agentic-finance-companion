import pytest
from cryptography.fernet import Fernet

from app.config import get_settings
from app.security import TokenEncryptionError, decrypt_token, encrypt_token


def test_round_trip(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TOKEN_ENCRYPTION_KEY", Fernet.generate_key().decode())
    get_settings.cache_clear()
    ciphertext = encrypt_token("access-sandbox-123")
    assert "access-sandbox-123" not in ciphertext
    assert decrypt_token(ciphertext) == "access-sandbox-123"


def test_missing_key_is_an_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TOKEN_ENCRYPTION_KEY", "")
    get_settings.cache_clear()
    with pytest.raises(TokenEncryptionError):
        encrypt_token("x")
