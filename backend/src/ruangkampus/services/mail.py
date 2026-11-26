import html
import logging
import smtplib
from email.message import EmailMessage
from pathlib import Path
from uuid import uuid4

import httpx

from ruangkampus.config import get_settings

logger = logging.getLogger(__name__)
_TEMPLATE_PATH = Path(__file__).resolve().parent.parent / "templates" / "email.html"


def render_html_email(
    title: str,
    body: str,
    action_url: str | None = None,
    action_label: str | None = None,
) -> str:
    """Render the shared HTML email template with all user-controlled text escaped."""
    template = _TEMPLATE_PATH.read_text(encoding="utf-8")
    safe_title = html.escape(title)
    safe_body = "<br>".join(html.escape(line) for line in body.splitlines())
    action_html = ""
    if action_url and action_label:
        safe_url = html.escape(action_url, quote=True)
        safe_label = html.escape(action_label)
        action_html = (
            '<p style="margin:24px 0 0;">'
            f'<a href="{safe_url}" style="display:inline-block;padding:12px 18px;'
            'background:#173b69;color:#ffffff;text-decoration:none;border-radius:8px;">'
            f"{safe_label}</a></p>"
        )
    return (
        template.replace("{{ title }}", safe_title)
        .replace("{{ message_html }}", safe_body)
        .replace("{{ action_html }}", action_html)
    )


def send_email(
    to_email: str,
    subject: str,
    body: str,
    html_body: str | None = None,
) -> bool:
    """Send through Brevo API, SMTP, or the local-only development mailbox."""
    settings = get_settings()
    if settings.email_backend == "console":
        if settings.is_production:
            raise RuntimeError("Console email backend is disabled in production")
        mailbox = Path(settings.local_mailbox_dir)
        mailbox.mkdir(parents=True, exist_ok=True)
        path = mailbox / f"{uuid4().hex}.eml.txt"
        content = f"To: {to_email}\nSubject: {subject}\n\n{body}\n"
        if html_body:
            content += f"\n--- HTML ALTERNATIVE ---\n{html_body}\n"
        path.write_text(content, encoding="utf-8")
        try:
            path.chmod(0o600)
        except OSError:
            logger.warning("Could not restrict local mailbox file permissions")
        logger.info("Development email message written to local mailbox file")
        return True

    if settings.email_backend == "disabled":
        logger.info("Email delivery is disabled; no message was sent")
        return False

    if settings.email_backend == "brevo":
        if not settings.brevo_api_key or not settings.brevo_sender_email:
            logger.warning("Brevo email provider is not configured; no email was sent")
            return False
        html_content = html_body or (
            "<html><body><p>"
            + "<br>".join(html.escape(line) for line in body.splitlines())
            + "</p></body></html>"
        )
        response = httpx.post(
            "https://api.brevo.com/v3/smtp/email",
            headers={
                "accept": "application/json",
                "api-key": settings.brevo_api_key,
                "content-type": "application/json",
            },
            json={
                "sender": {
                    "name": settings.brevo_sender_name,
                    "email": settings.brevo_sender_email,
                },
                "to": [{"email": to_email}],
                "subject": subject,
                "htmlContent": html_content,
            },
            timeout=settings.smtp_timeout_seconds,
        )
        response.raise_for_status()
        logger.info("Transactional email accepted by Brevo")
        return True

    if settings.email_backend != "smtp" or not settings.smtp_host:
        logger.warning("Email provider is not configured; no email was sent")
        return False

    message = EmailMessage()
    message["From"] = settings.smtp_from_email
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(body)
    if html_body:
        message.add_alternative(html_body, subtype="html")

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=settings.smtp_timeout_seconds) as smtp:
        smtp.ehlo()
        if settings.smtp_use_tls:
            smtp.starttls()
            smtp.ehlo()
        if settings.smtp_username:
            smtp.login(settings.smtp_username, settings.smtp_password or "")
        refused_recipients = smtp.send_message(message)
    return not bool(refused_recipients)
