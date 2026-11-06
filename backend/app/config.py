"""Application settings, read from environment variables (and a local `.env` file).

Every field has a development default so the app, the tests, and the OpenAPI export
run without any credentials. Real providers are opt-in through the `*_PROVIDER` settings.
"""

from functools import lru_cache
from typing import Literal

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", "../.env"), extra="ignore")

    app_env: Literal["development", "test", "production"] = "development"
    database_url: str = "postgresql+psycopg://finance:finance@localhost:5432/finance"
    # Fernet key used to encrypt Plaid access tokens at rest. Generate one with
    # `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`.
    token_encryption_key: SecretStr = SecretStr("")

    # Authentication (OAuth 2.0 / OpenID Connect)
    auth_provider: Literal["mock", "oidc"] = "mock"
    oidc_issuer: str = ""
    oidc_audience: str = ""
    oidc_client_id: str = ""

    # Plaid
    plaid_provider: Literal["mock", "plaid"] = "mock"
    plaid_env: Literal["sandbox", "production"] = "sandbox"
    plaid_client_id: str = ""
    plaid_secret: SecretStr = SecretStr("")
    plaid_webhook_url: str = ""

    # LLM: "openai" = OpenAI-style /chat/completions, "anthropic" = Anthropic-style /messages
    llm_provider: Literal["mock", "openai", "anthropic"] = "mock"
    llm_base_url: str = ""
    llm_api_key: SecretStr = SecretStr("")
    llm_model: str = ""

    @model_validator(mode="after")
    def _check_real_providers(self) -> "Settings":
        missing: list[str] = []
        if self.auth_provider == "oidc" and not (self.oidc_issuer and self.oidc_audience):
            missing += ["OIDC_ISSUER", "OIDC_AUDIENCE"]
        if self.plaid_provider == "plaid":
            if not self.plaid_client_id:
                missing.append("PLAID_CLIENT_ID")
            if not self.plaid_secret.get_secret_value():
                missing.append("PLAID_SECRET")
        if self.llm_provider != "mock":
            if not self.llm_base_url:
                missing.append("LLM_BASE_URL")
            if not self.llm_model:
                missing.append("LLM_MODEL")
        if missing:
            raise ValueError(f"Missing required settings: {', '.join(missing)}")
        if self.app_env == "production" and "mock" in (
            self.auth_provider,
            self.plaid_provider,
            self.llm_provider,
        ):
            raise ValueError("Mock providers are not allowed when APP_ENV=production")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
