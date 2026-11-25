from functools import lru_cache
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", "backend/.env"), env_file_encoding="utf-8", extra="ignore", case_sensitive=False)
    app_env: str = "development"
    app_name: str = "RuangKampus API"
    api_v1_prefix: str = "/api/v1"
    database_url: str = "sqlite:///./ruangkampus_local.db"
    jwt_secret_key: str = "local-only-insecure-secret-change-before-use"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 14
    password_reset_expire_minutes: int = 30
    cors_origins: list[str] = ["http://localhost:5173"]
    cookie_secure: bool = False
    cookie_samesite: str = "lax"
    email_backend: str = "console"
    local_mailbox_dir: str = ".local_mailbox"
    password_reset_base_url: str = "http://localhost:5173/reset-password"
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from_email: str = "no-reply@example.invalid"
    smtp_use_tls: bool = True
    smtp_timeout_seconds: int = 10
    campus_timezone: str = "Asia/Jakarta"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value):
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator("cookie_samesite")
    @classmethod
    def validate_samesite(cls, value: str) -> str:
        value = value.lower()
        if value not in {"lax", "strict", "none"}:
            raise ValueError("COOKIE_SAMESITE must be lax, strict, or none")
        return value

    @model_validator(mode="after")
    def validate_production_configuration(self):
        if self.app_env.lower() == "production":
            if len(self.jwt_secret_key.encode("utf-8")) < 32 or "change" in self.jwt_secret_key.lower():
                raise ValueError("Production requires a strong JWT_SECRET_KEY (32+ bytes)")
            if not self.database_url.startswith(("postgresql://", "postgresql+psycopg://")):
                raise ValueError("Production DATABASE_URL must use PostgreSQL")
            if self.email_backend != "smtp" or not self.smtp_host or not self.smtp_username:
                raise ValueError("Production requires EMAIL_BACKEND=smtp and SMTP configuration")
            if not self.cookie_secure:
                raise ValueError("Production requires COOKIE_SECURE=true")
            if self.email_backend == "console":
                raise ValueError("Console email backend is development-only; configure SMTP or disabled")
            if self.email_backend == "smtp" and not self.smtp_host:
                raise ValueError("EMAIL_BACKEND=smtp requires SMTP_HOST")
            if self.email_backend == "smtp" and not self.smtp_use_tls:
                raise ValueError("Production SMTP must use STARTTLS (SMTP_USE_TLS=true)")
            if self.cookie_samesite == "none" and not self.cookie_secure:
                raise ValueError("SameSite=None requires COOKIE_SECURE=true")
            if "*" in self.cors_origins:
                raise ValueError("Production CORS_ORIGINS must list explicit trusted origins")
        return self

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


def reset_settings_cache() -> None:
    get_settings.cache_clear()
