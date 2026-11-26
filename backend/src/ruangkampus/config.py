from functools import lru_cache
from typing import Annotated
from pydantic import Field, field_validator, model_validator
from urllib.parse import urlsplit
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


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
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:5173"]
    cookie_secure: bool = False
    cookie_samesite: str = "lax"
    email_backend: str = "console"
    local_mailbox_dir: str = ".local_mailbox"
    public_app_url: str = "http://localhost:5173"
    password_reset_base_url: str = "http://localhost:5173/reset-password"
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from_email: str = "no-reply@example.invalid"
    smtp_use_tls: bool = True
    smtp_timeout_seconds: int = 10
    brevo_api_key: str | None = None
    brevo_sender_email: str | None = None
    # Backward-compatible alias for the existing Railway variable name.
    brevo_sender_mail: str | None = None
    brevo_sender_name: str = "RuangKampus"
    campus_timezone: str = "Asia/Jakarta"
    room_media_dir: str = ".room-media"
    # Optional OpenAI-compatible endpoint. Disabled by default; no provider is called unless enabled.
    assistant_ai_enabled: bool = False
    assistant_ai_endpoint_url: str | None = None
    assistant_ai_model: str | None = None
    assistant_ai_api_key: str | None = None
    assistant_ai_timeout_seconds: float = Field(default=4.0, gt=0, le=8)

    @field_validator("email_backend", mode="before")
    @classmethod
    def normalize_email_backend(cls, value):
        if isinstance(value, str):
            return value.strip().lower()
        return value

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
            if not self.cookie_secure:
                raise ValueError("Production requires COOKIE_SECURE=true")
            if self.cookie_samesite == "none" and not self.cookie_secure:
                raise ValueError("SameSite=None requires COOKIE_SECURE=true")
            if "*" in self.cors_origins:
                raise ValueError("Production CORS_ORIGINS must list explicit trusted origins")

            # In-app notifications remain available even when outbound email is disabled.
            if self.email_backend == "console":
                raise ValueError("Console email backend is development-only; use smtp, brevo or disabled")
            if self.email_backend not in {"smtp", "brevo", "disabled"}:
                raise ValueError("Production EMAIL_BACKEND must be smtp, brevo or disabled")
            if self.email_backend == "smtp":
                if not self.smtp_host or not self.smtp_username:
                    raise ValueError("EMAIL_BACKEND=smtp requires SMTP_HOST and SMTP_USERNAME")
                if not self.smtp_use_tls:
                    raise ValueError("Production SMTP must use STARTTLS (SMTP_USE_TLS=true)")
            if self.email_backend == "brevo":
                sender_email = self.brevo_sender_email or self.brevo_sender_mail
                if not self.brevo_api_key or not sender_email:
                    raise ValueError(
                        "EMAIL_BACKEND=brevo requires BREVO_API_KEY and BREVO_SENDER_EMAIL "
                        "(BREVO_SENDER_MAIL is also accepted)"
                    )
                if "@" not in sender_email:
                    raise ValueError("BREVO_SENDER_EMAIL must be a valid email address (BREVO_SENDER_MAIL is also accepted)")
        return self

    @model_validator(mode="after")
    def validate_assistant_ai_configuration(self):
        if not self.assistant_ai_enabled:
            return self
        if not self.assistant_ai_endpoint_url or not self.assistant_ai_model:
            raise ValueError("ASSISTANT_AI_ENABLED requires ASSISTANT_AI_ENDPOINT_URL and ASSISTANT_AI_MODEL")
        parsed = urlsplit(self.assistant_ai_endpoint_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.username or parsed.password:
            raise ValueError("ASSISTANT_AI_ENDPOINT_URL must be an absolute HTTP(S) URL without embedded credentials")
        if self.assistant_ai_timeout_seconds > 8:
            raise ValueError("ASSISTANT_AI_TIMEOUT_SECONDS must not exceed 8 seconds")
        return self

    @property
    def brevo_sender_address(self) -> str | None:
        """Return the configured Brevo sender, accepting the legacy Railway variable."""
        return self.brevo_sender_email or self.brevo_sender_mail

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


def reset_settings_cache() -> None:
    get_settings.cache_clear()
