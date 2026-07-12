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
    private_files_enabled: bool = True
    private_files_backend: str = Field(default="local", validation_alias=AliasChoices("PRIVATE_FILES_BACKEND", "FILE_STORAGE_PROVIDER"))
    private_files_bucket: str = Field(default="financy-private", validation_alias=AliasChoices("PRIVATE_FILES_BUCKET", "SUPABASE_STORAGE_BUCKET"))
    private_files_max_size_bytes: int = 10 * 1024 * 1024
    private_files_signed_url_ttl_seconds: int = Field(default=300, validation_alias=AliasChoices("PRIVATE_FILES_SIGNED_URL_TTL_SECONDS", "SIGNED_URL_TTL_SECONDS"))
    private_files_allowed_mime_types: str = "image/jpeg,image/png,image/webp,application/pdf"
    private_files_scan_provider: str = Field(default="mock", validation_alias=AliasChoices("PRIVATE_FILES_SCAN_PROVIDER", "FILE_SCAN_PROVIDER"))
    private_files_orphan_retention_hours: int = 24
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

    @property
    def private_files_allowed_mime_type_list(self) -> list[str]:
        return [item.strip() for item in self.private_files_allowed_mime_types.split(",") if item.strip()]

    def validate_private_files_config(self) -> None:
        if not self.private_files_enabled:
            return
        backend = self.private_files_backend.strip().lower()
        if backend not in {"local", "supabase"}:
            raise RuntimeError("PRIVATE_FILES_BACKEND must be 'local' or 'supabase'.")
        if backend == "supabase" and (not self.supabase_url or not self.supabase_service_role_key):
            raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required when PRIVATE_FILES_BACKEND=supabase.")
        if self.private_files_max_size_bytes <= 0:
            raise RuntimeError("PRIVATE_FILES_MAX_SIZE_BYTES must be greater than zero.")
        if self.private_files_signed_url_ttl_seconds <= 0:
            raise RuntimeError("PRIVATE_FILES_SIGNED_URL_TTL_SECONDS must be greater than zero.")
        if self.private_files_orphan_retention_hours < 0:
            raise RuntimeError("PRIVATE_FILES_ORPHAN_RETENTION_HOURS cannot be negative.")


settings = Settings()
