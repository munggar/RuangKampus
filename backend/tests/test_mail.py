from types import SimpleNamespace

from ruangkampus.services import mail


def test_html_email_escapes_untrusted_content():
    result = mail.render_html_email(
        "Notice <script>alert(1)</script>",
        "Hello <img src=x onerror=alert(1)>",
        "https://example.com/reset?token=a&b=c",
        "Reset & continue",
    )
    assert "<script>" not in result
    assert "<img src=x" not in result
    assert "&lt;script&gt;" in result
    assert "&amp;" in result


def test_smtp_delivery_uses_tls_and_html_alternative(monkeypatch):
    captured = {}

    class FakeSMTP:
        def __init__(self, host, port, timeout):
            captured["connection"] = (host, port, timeout)

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def ehlo(self):
            captured["ehlo"] = captured.get("ehlo", 0) + 1

        def starttls(self):
            captured["tls"] = True

        def login(self, username, password):
            captured["login"] = (username, password)

        def send_message(self, message):
            captured["message"] = message
            return {}

    monkeypatch.setattr(mail, "get_settings", lambda: SimpleNamespace(
        email_backend="smtp", is_production=True, smtp_host="smtp.test.invalid", smtp_port=587,
        smtp_timeout_seconds=8, smtp_use_tls=True, smtp_username="mailer", smtp_password="secret",
        smtp_from_email="no-reply@example.test",
    ))
    monkeypatch.setattr(mail.smtplib, "SMTP", FakeSMTP)
    delivered = mail.send_email("student@example.test", "Test", "Plain body", "<p>HTML body</p>")
    assert delivered is True
    assert captured["tls"] is True
    assert captured["login"] == ("mailer", "secret")
    message = captured["message"]
    alternatives = list(message.iter_parts())
    assert len(alternatives) == 2
    assert alternatives[0].get_content_type() == "text/plain"
    assert alternatives[0].get_content() == "Plain body\n"
    assert alternatives[1].get_content_type() == "text/html"
    assert "HTML body" in alternatives[1].get_content()


def test_development_mailbox_does_not_claim_smtp_delivery(monkeypatch, tmp_path):
    monkeypatch.setattr(mail, "get_settings", lambda: SimpleNamespace(
        email_backend="console", is_production=False, local_mailbox_dir=str(tmp_path),
    ))
    assert mail.send_email("student@example.test", "Subject", "Body", "<p>Body</p>") is True
    files = list(tmp_path.glob("*.eml.txt"))
    assert len(files) == 1
    content = files[0].read_text(encoding="utf-8")
    assert "Subject: Subject" in content
    assert "HTML ALTERNATIVE" in content
    assert files[0].stat().st_mode & 0o777 == 0o600
