import pytest
from pydantic import ValidationError

from app.config import Settings


def test_defaults_use_mock_providers() -> None:
    s = Settings(_env_file=None)
    assert (s.auth_provider, s.plaid_provider, s.llm_provider) == ("mock", "mock", "mock")


def test_real_providers_require_credentials() -> None:
    with pytest.raises(ValidationError, match=r"PLAID_CLIENT_ID.*PLAID_SECRET"):
        Settings(_env_file=None, plaid_provider="plaid")
    with pytest.raises(ValidationError, match=r"LLM_BASE_URL.*LLM_MODEL"):
        Settings(_env_file=None, llm_provider="openai")
    with pytest.raises(ValidationError, match="OIDC_ISSUER"):
        Settings(_env_file=None, auth_provider="oidc")


def test_production_refuses_mocks() -> None:
    with pytest.raises(ValidationError, match="not allowed"):
        Settings(_env_file=None, app_env="production")
