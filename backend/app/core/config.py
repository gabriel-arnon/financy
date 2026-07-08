from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Financy API"
    environment: str = Field(default="local", validation_alias=AliasChoices("APP_ENV", "ENVIRONMENT"))
    dev_user_id: str = "00000000-0000-4000-8000-000000000001"
    upload_dir: Path = Field(default=Path(".uploads"), validation_alias=AliasChoices("UPLOAD_STORAGE_PATH", "UPLOAD_DIR"))
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    supabase_url: str | None = None
    supabase_service_role_key: str | None = None
    database_url: str | None = None
    test_database_url: str | None = None
    storage_backend: str = "json"
    auth_provider: str = "supabase"
    auth_required: bool = False
    auth_dev_bypass: bool = True
    supabase_jwt_issuer: str | None = None
    supabase_jwks_url: str | None = None
    supabase_audience: str | None = None
    jwt_secret: str = "change-me-local-only"
    ai_import_enabled: bool = False
    ai_import_provider: str = "openai-compatible"
    ai_import_base_url: str = "https://api.openai.com/v1"
    ai_import_api_key: str | None = None
    ai_import_model: str = "gpt-4o-mini"
    ai_import_timeout_seconds: float = 45.0

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def allows_dev_auth_bypass(self) -> bool:
        return self.auth_dev_bypass and self.environment.lower() in {"local", "development", "test"}


settings = Settings()
