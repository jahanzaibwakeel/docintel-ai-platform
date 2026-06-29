from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AI Document Intelligence Platform"
    api_prefix: str = "/api/v1"
    log_level: str = "INFO"
    json_logs: bool = True
    database_url: str = "postgresql+psycopg://docintel:docintel@localhost:5432/docintel"
    redis_url: str = "redis://localhost:6379/0"
    secret_key: str = "dev-secret-change-me"
    access_token_expire_minutes: int = 1440
    refresh_token_expire_days: int = 30
    password_reset_expire_minutes: int = 30
    password_reset_return_token: bool = True
    workspace_invite_expire_days: int = 14
    email_provider: str = "outbox"
    email_from: str = "DocIntel <no-reply@docintel.local>"
    email_outbox_dir: Path = Path("email-outbox")
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_use_tls: bool = True
    admin_emails: str = ""
    rate_limit_enabled: bool = True
    rate_limit_per_minute: int = 120
    frontend_origin: str = "http://localhost:3000"
    upload_dir: Path = Path("uploads")
    storage_provider: str = "local"
    storage_bucket: str | None = None
    storage_endpoint_url: str | None = None
    storage_region: str = "us-east-1"
    storage_access_key_id: str | None = None
    storage_secret_access_key: str | None = None
    storage_presign_seconds: int = 300
    max_upload_mb: int = 25
    default_retention_days: int = 0
    allow_external_ai_with_pii: bool = False
    redact_pii_for_external_ai: bool = True
    enable_ocr: bool = True
    ocr_min_chars_per_page: int = 40
    ocr_dpi: int = 220
    chunk_size: int = 1200
    chunk_overlap: int = 160
    embedding_dimensions: int = 1536

    ai_provider: str = "fallback"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4.1-mini"
    openai_embedding_model: str = "text-embedding-3-small"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1"
    ollama_embedding_model: str = "nomic-embed-text"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    return settings
