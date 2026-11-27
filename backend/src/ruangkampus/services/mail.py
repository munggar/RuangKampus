import html
import logging
import smtplib
from email.message import EmailMessage
from email.utils import formataddr
from pathlib import Path
from uuid import uuid4

import httpx

from ruangkampus.config import get_settings

logger = logging.getLogger(__name__)
_TEMPLATE_PATH = Path(__file__).resolve().parent.parent / "templates" / "email.html"


def _branded_sender_name(configured_name: str | None) -> str:
    """Keep the configured sender label while consistently identifying CodeMu and UHAMKA."""
    base_name = (configured_name or "RuangKampus").strip() or "RuangKampus"
    additions = []
    if "codemu" not in base_name.casefold():
        additions.append("Tim CodeMu")
    if "uhamka" not in base_name.casefold():
        additions.append("UHAMKA")
    return " · ".join([base_name, *additions])


def render_html_email(
    title: str,
    body: str,
    action_url: str | None = None,
    action_label: str | None = None,
    *,
    preheader: str | None = None,
    eyebrow: str = "PEMBARUAN RUANGKAMPUS",
    details: list[tuple[str, str]] | None = None,
    accent_color: str = "#2f68dc",
    footer_note: str = "Pesan ini dikirim otomatis oleh RuangKampus. Mohon jangan membalas email ini.",
) -> str:
    """Render the branded transactional email. All dynamic text and URLs are escaped."""
    template = _TEMPLATE_PATH.read_text(encoding="utf-8")
    settings = get_settings()
    app_url = getattr(settings, "public_app_url", "http://localhost:5173").rstrip("/")
    brand_logo_url = html.escape(f"{app_url}/brand/logo-primary.png", quote=True)
    safe_title = html.escape(title)
    safe_body = "<br>".join(html.escape(line) for line in body.splitlines())
    preheader_text = preheader or (body.splitlines()[0] if body else "Pembaruan dari RuangKampus")
    safe_preheader = html.escape(preheader_text)
    safe_eyebrow = html.escape(eyebrow)
    safe_footer_note = html.escape(footer_note)

    details_html = ""
    if details:
        rows = []
        for label, value in details:
            rows.append(
                '<tr><td style="padding:11px 14px;color:#69778d;font-size:13px;'
                'border-bottom:1px solid #e8edf5;width:38%;">'
                f"{html.escape(str(label))}</td>"
                '<td style="padding:11px 14px;color:#17243b;font-size:13px;font-weight:700;'
                'border-bottom:1px solid #e8edf5;">'
                f"{html.escape(str(value))}</td></tr>"
            )
        details_html = (
            '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
            'style="margin:24px 0 4px;border:1px solid #e5eaf3;border-radius:14px;'
            'border-collapse:separate;border-spacing:0;overflow:hidden;background:#f8faff;">'
            + "".join(rows)
            + "</table>"
        )

    action_html = ""
    if action_url and action_label:
        safe_url = html.escape(action_url, quote=True)
        safe_label = html.escape(action_label)
        action_html = (
            '<table role="presentation" cellpadding="0" cellspacing="0" style="margin:26px 0 8px;">'
            '<tr><td align="center" bgcolor="' + html.escape(accent_color, quote=True) + '" '
            'style="border-radius:12px;">'
            f'<a href="{safe_url}" style="display:inline-block;padding:14px 24px;'
            'font-family:Arial,Helvetica,sans-serif;font-size:14px;font-weight:700;'
            'color:#ffffff;text-decoration:none;border-radius:12px;">'
            f"{safe_label} &nbsp; &#8599;</a></td></tr></table>"
            '<p style="margin:12px 0 0;color:#7a879b;font-size:11px;line-height:1.6;">'
            'Jika tombol tidak terbuka, salin tautan berikut ke browser:<br>'
            f'<a href="{safe_url}" style="color:#315fc7;word-break:break-all;text-decoration:underline;">'
            f"{safe_url}</a></p>"
        )

    replacements = {
        "{{ title }}": safe_title,
        "{{ brand_logo_url }}": brand_logo_url,
        "{{ preheader }}": safe_preheader,
        "{{ eyebrow }}": safe_eyebrow,
        "{{ message_html }}": safe_body,
        "{{ details_html }}": details_html,
        "{{ action_html }}": action_html,
        "{{ footer_note }}": safe_footer_note,
    }
    for token, value in replacements.items():
        template = template.replace(token, value)
    return template


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
        sender_email = (
            getattr(settings, "brevo_sender_address", None)
            or getattr(settings, "brevo_sender_email", None)
            or getattr(settings, "brevo_sender_mail", None)
        )
        if not settings.brevo_api_key or not sender_email:
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
                    "name": _branded_sender_name(settings.brevo_sender_name),
                    "email": sender_email,
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
    message["From"] = formataddr((_branded_sender_name(getattr(settings, "brevo_sender_name", "RuangKampus")), settings.smtp_from_email))
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
