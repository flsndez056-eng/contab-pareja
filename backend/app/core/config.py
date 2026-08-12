from functools import lru_cache
from typing import Literal

from pydantic import EmailStr, Field, HttpUrl, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        case_sensitive=False,
        extra="ignore",
    )

    app_env: Literal["development", "test", "staging", "production"] = "development"
    app_name: str = "DúoCuenta API"
    api_v1_prefix: str = "/api/v1"
    database_url: str
    jwt_secret: str = Field(min_length=64)
    access_token_minutes: int = Field(default=15, ge=5, le=60)
    refresh_token_days: int = Field(default=30, ge=1, le=90)
    password_reset_minutes: int = Field(default=15, ge=5, le=60)
    email_verification_hours: int = Field(default=24, ge=1, le=72)
    email_action_cooldown_seconds: int = Field(default=60, ge=30, le=900)
    cors_origins: list[str] = []
    fcm_project_id: str | None = None
    google_application_credentials: str | None = None
    email_delivery_mode: Literal["disabled", "smtp"] = "disabled"
    email_from_address: EmailStr | None = None
    smtp_host: str | None = None
    smtp_port: int = Field(default=587, ge=1, le=65535)
    smtp_username: str | None = None
    smtp_password: SecretStr | None = None
    smtp_starttls: bool = True
    smtp_timeout_seconds: int = Field(default=10, ge=3, le=30)
    android_deep_link_base: str = "contabpareja://auth"
    account_action_base_url: HttpUrl = HttpUrl(
        "https://contab.siptrapollo.online/auth"
    )
    invitation_base_url: HttpUrl = HttpUrl("https://contab.siptrapollo.online/invite")
    android_app_cert_sha256: str = ""

    @field_validator("database_url")
    @classmethod
    def require_postgresql(cls, value: str) -> str:
        if not value.startswith(("postgresql+psycopg://", "postgresql://")):
            raise ValueError("DATABASE_URL debe usar PostgreSQL.")
        return value

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
