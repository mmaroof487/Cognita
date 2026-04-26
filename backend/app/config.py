"""
FastAPI configuration via Pydantic Settings.
Loads from environment variables with type validation.
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # ─────────────────────────────────────────────────────────────────────────
    # DATABASE
    # ─────────────────────────────────────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://devpulse:devpulse@localhost/devpulse"
    database_url_sync: str = "postgresql://devpulse:devpulse@localhost/devpulse"

    # ─────────────────────────────────────────────────────────────────────────
    # REDIS
    # ─────────────────────────────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"

    # ─────────────────────────────────────────────────────────────────────────
    # GITHUB OAUTH
    # ─────────────────────────────────────────────────────────────────────────
    github_client_id: str
    github_client_secret: str
    github_access_token: Optional[str] = None

    # ─────────────────────────────────────────────────────────────────────────
    # JWT & ENCRYPTION
    # ─────────────────────────────────────────────────────────────────────────
    jwt_secret: str
    jwt_expire_minutes: int = 15
    jwt_refresh_expire_days: int = 7
    encryption_key: str  # Fernet key, generated via cryptography

    # ─────────────────────────────────────────────────────────────────────────
    # ANTHROPIC (LLMs)
    # ─────────────────────────────────────────────────────────────────────────
    anthropic_api_key: str
    anthropic_model: str = "claude-3-sonnet-20240229"

    # ─────────────────────────────────────────────────────────────────────────
    # NOTIFICATIONS
    # ─────────────────────────────────────────────────────────────────────────
    slack_webhook_url: Optional[str] = None
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = None
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    notification_email: Optional[str] = None
    jira_base_url: Optional[str] = None
    jira_api_user: Optional[str] = None
    jira_api_token: Optional[str] = None
    jira_project_key: Optional[str] = None

    # ─────────────────────────────────────────────────────────────────────────
    # SERVER
    # ─────────────────────────────────────────────────────────────────────────
    environment: str = "development"
    debug: bool = True
    cors_origins: str = "http://localhost:3000,http://localhost:3001"
    log_level: str = "INFO"

    # ─────────────────────────────────────────────────────────────────────────
    # CELERY
    # ─────────────────────────────────────────────────────────────────────────
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"

    # ─────────────────────────────────────────────────────────────────────────
    # OPENTELEMETRY
    # ─────────────────────────────────────────────────────────────────────────
    otel_exporter_otlp_endpoint: str = "http://localhost:4317"
    enable_telemetry: bool = False

    # ─────────────────────────────────────────────────────────────────────────
    # RATE LIMITING
    # ─────────────────────────────────────────────────────────────────────────
    rate_limit_default: int = 60  # requests per minute

    class Config:
        env_file = ".env"
        case_sensitive = False

    def get_cors_origins(self) -> list[str]:
        """Parse CORS origins from comma-separated string."""
        return [origin.strip() for origin in self.cors_origins.split(",")]


# Global settings instance
settings = Settings()
