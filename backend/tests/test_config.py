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


def test_production_brevo_requires_api_key_and_verified_sender():
    with pytest.raises(ValidationError, match="BREVO_API_KEY and BREVO_SENDER_EMAIL"):
        production_settings(email_backend="brevo")


def test_production_brevo_accepts_api_key_and_sender_configuration():
    settings = production_settings(
        email_backend="brevo",
        brevo_api_key="xkeysib-test-secret",
        brevo_sender_email="notifications@example.test",
        brevo_sender_name="RuangKampus",
    )
    assert settings.email_backend == "brevo"
    assert settings.brevo_sender_email == "notifications@example.test"


def test_production_brevo_rejects_invalid_sender_email():
    with pytest.raises(ValidationError, match="BREVO_SENDER_EMAIL must be a valid email address"):
        production_settings(
            email_backend="brevo",
            brevo_api_key="xkeysib-test-secret",
            brevo_sender_email="not-an-email",
        )
