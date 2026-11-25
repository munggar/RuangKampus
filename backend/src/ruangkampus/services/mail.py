import logging
import smtplib
from email.message import EmailMessage
from pathlib import Path
from uuid import uuid4

from ruangkampus.config import get_settings

logger = logging.getLogger(__name__)


def send_email(to_email: str, subject: str, body: str) -> bool:
    """Send email through SMTP or write a local-only message file in development."""
    settings = get_settings()
    if settings.email_backend == "console":
        if settings.is_production:
            raise RuntimeError("Console email backend is disabled in production")
        mailbox = Path(settings.local_mailbox_dir)
        mailbox.mkdir(parents=True, exist_ok=True)
        path = mailbox / f"{uuid4().hex}.eml.txt"
        path.write_text(f"To: {to_email}\nSubject: {subject}\n\n{body}\n", encoding="utf-8")
        try:
            path.chmod(0o600)
        except OSError:
            logger.warning("Could not restrict local mailbox file permissions")
        logger.info("Development email message written to local mailbox file: %s", path)
        return True

    if settings.email_backend == "disabled" or settings.email_backend != "smtp" or not settings.smtp_host:
        logger.warning("Email provider is not configured; no email was sent")
        return False

    message = EmailMessage()
    message["From"] = settings.smtp_from_email
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(body)
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=settings.smtp_timeout_seconds) as smtp:
        if settings.smtp_use_tls:
            smtp.starttls()
        if settings.smtp_username:
            smtp.login(settings.smtp_username, settings.smtp_password or "")
        smtp.send_message(message)
    return True
