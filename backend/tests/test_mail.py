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



def test_brevo_delivery_uses_transactional_email_api(monkeypatch):
    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            captured["raised_for_status"] = True

    def fake_post(url, *, headers, json, timeout):
        captured["url"] = url
        captured["headers"] = headers
        captured["payload"] = json
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr(mail.httpx, "post", fake_post)
    monkeypatch.setattr(mail, "get_settings", lambda: SimpleNamespace(
        email_backend="brevo",
        brevo_api_key="xkeysib-test-secret",
        brevo_sender_email="notifications@example.test",
        brevo_sender_name="RuangKampus",
        smtp_timeout_seconds=9,
    ))

    delivered = mail.send_email(
        "student@example.test",
        "Reservation approved",
        "Your reservation is approved.",
        "<html><body><p>Your reservation is approved.</p></body></html>",
    )

    assert delivered is True
    assert captured["url"] == "https://api.brevo.com/v3/smtp/email"
    assert captured["headers"]["api-key"] == "xkeysib-test-secret"
    assert captured["payload"] == {
        "sender": {"name": "RuangKampus", "email": "notifications@example.test"},
        "to": [{"email": "student@example.test"}],
        "subject": "Reservation approved",
        "htmlContent": "<html><body><p>Your reservation is approved.</p></body></html>",
    }
    assert captured["timeout"] == 9
    assert captured["raised_for_status"] is True


def test_brevo_delivery_falls_back_to_escaped_html(monkeypatch):
    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

    def fake_post(url, *, headers, json, timeout):
        captured["payload"] = json
        return FakeResponse()

    monkeypatch.setattr(mail.httpx, "post", fake_post)
    monkeypatch.setattr(mail, "get_settings", lambda: SimpleNamespace(
        email_backend="brevo",
        brevo_api_key="xkeysib-test-secret",
        brevo_sender_email="notifications@example.test",
        brevo_sender_name="RuangKampus",
        smtp_timeout_seconds=9,
    ))

    assert mail.send_email("student@example.test", "Notice", "<hello>") is True
    assert "&lt;hello&gt;" in captured["payload"]["htmlContent"]



def test_brevo_uses_legacy_sender_mail_setting(monkeypatch):
    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

    def fake_post(url, *, headers, json, timeout):
        captured["payload"] = json
        return FakeResponse()

    monkeypatch.setattr(mail.httpx, "post", fake_post)
    monkeypatch.setattr(mail, "get_settings", lambda: SimpleNamespace(
        email_backend="brevo",
        brevo_api_key="xkeysib-test-secret",
        brevo_sender_email=None,
        brevo_sender_mail="notifications@example.test",
        brevo_sender_address="notifications@example.test",
        brevo_sender_name="RuangKampus",
        smtp_timeout_seconds=9,
    ))

    assert mail.send_email("student@example.test", "Notice", "Body") is True
    assert captured["payload"]["sender"]["email"] == "notifications@example.test"



def test_branded_email_includes_details_button_and_fallback_link():
    result = mail.render_html_email(
        "Reservasi kamu disetujui",
        "Kabar baik! Ruangan sudah disiapkan untuk jadwalmu.",
        "https://ruangkampus.example/student/reservations/abc-123",
        "Lihat detail reservasi",
        preheader="Reservasi disetujui.",
        eyebrow="RESERVASI DISETUJUI",
        details=[("Ruangan", "Lab Komputer"), ("Tanggal", "30/11/2026")],
        accent_color="#159b70",
    )
    assert "RuangKampus" in result
    assert "RESERVASI DISETUJUI" in result
    assert "Lab Komputer" in result
    assert "30/11/2026" in result
    assert 'href="https://ruangkampus.example/student/reservations/abc-123"' in result
    assert "Lihat detail reservasi" in result
    assert "salin tautan berikut" in result
