import pytest
from pydantic import ValidationError

from ruangkampus.config import Settings


def production_settings(**overrides):
    values = {
        "app_env": "production",
        "database_url": "postgresql+psycopg://user:password@db.internal:5432/ruangkampus",
        "jwt_secret_key": "a" * 64,
        "cors_origins": ["https://ruangkampus.example"],
        "cookie_secure": True,
        "cookie_samesite": "lax",
        "email_backend": "disabled",
    }
    values.update(overrides)
    return Settings(**values)


def test_production_can_explicitly_disable_outbound_email():
    settings = production_settings()
    assert settings.is_production
    assert settings.email_backend == "disabled"


def test_production_rejects_console_mailbox():
    with pytest.raises(ValidationError, match="Console email backend is development-only"):
        production_settings(email_backend="console")


def test_production_smtp_requires_host_and_username():
    with pytest.raises(ValidationError, match="SMTP_HOST and SMTP_USERNAME"):
        production_settings(email_backend="smtp")


def test_production_smtp_requires_starttls():
    with pytest.raises(ValidationError, match="STARTTLS"):
        production_settings(
            email_backend="smtp",
            smtp_host="smtp.example.test",
            smtp_username="mailer",
            smtp_use_tls=False,
        )


def test_production_smtp_accepts_explicit_provider_configuration():
    settings = production_settings(
        email_backend="smtp",
        smtp_host="smtp.example.test",
        smtp_username="mailer",
        smtp_password="provider-secret",
        smtp_use_tls=True,
    )
    assert settings.email_backend == "smtp"
