from sqlalchemy import select

from ruangkampus import cli
from ruangkampus.models import User
from ruangkampus.security import verify_password


def set_bootstrap_env(monkeypatch, **overrides):
    values = {
        "RUANGKAMPUS_BOOTSTRAP_ADMIN_EMAIL": "first-admin@example.com",
        "RUANGKAMPUS_BOOTSTRAP_ADMIN_NAME": "First Administrator",
        "RUANGKAMPUS_BOOTSTRAP_ADMIN_PASSWORD": "VeryStrongTemporaryPassword-123!",
    }
    values.update(overrides)
    for key, value in values.items():
        monkeypatch.setenv(key, value)


def test_bootstrap_creates_first_active_admin_without_printing_password(db_session, monkeypatch, capsys):
    set_bootstrap_env(monkeypatch)
    monkeypatch.setattr(cli, "SessionLocal", lambda: db_session)

    cli.create_admin_from_env()

    admin = db_session.scalar(select(User).where(User.email == "first-admin@example.com"))
    assert admin is not None
    assert admin.role == "TU_ADMIN"
    assert admin.student_identifier == "admin.uhamka"
    assert admin.account_status == "ACTIVE"
    assert verify_password("VeryStrongTemporaryPassword-123!", admin.password_hash)
    output = capsys.readouterr().out
    assert "Bootstrap administrator created" in output
    assert "VeryStrongTemporaryPassword-123!" not in output


def test_bootstrap_is_idempotent_for_the_same_admin(db_session, admin, monkeypatch, capsys):
    set_bootstrap_env(monkeypatch, RUANGKAMPUS_BOOTSTRAP_ADMIN_EMAIL=admin.email)
    monkeypatch.setattr(cli, "SessionLocal", lambda: db_session)

    cli.create_admin_from_env()

    assert db_session.query(User).filter_by(role="TU_ADMIN").count() == 1
    assert "already exists" in capsys.readouterr().out


def test_bootstrap_refuses_to_promote_existing_student(db_session, student, monkeypatch):
    set_bootstrap_env(monkeypatch, RUANGKAMPUS_BOOTSTRAP_ADMIN_EMAIL=student.email)
    monkeypatch.setattr(cli, "SessionLocal", lambda: db_session)

    try:
        cli.create_admin_from_env()
    except SystemExit as exc:
        assert "non-administrator" in str(exc)
    else:
        raise AssertionError("Existing Student account must not be promoted by bootstrap")


def test_bootstrap_refuses_to_create_a_second_active_admin(db_session, admin, monkeypatch):
    set_bootstrap_env(monkeypatch)
    monkeypatch.setattr(cli, "SessionLocal", lambda: db_session)

    try:
        cli.create_admin_from_env()
    except SystemExit as exc:
        assert "restricted" in str(exc)
    else:
        raise AssertionError("Bootstrap must only create the first administrator")


def test_bootstrap_requires_strong_temporary_password(monkeypatch):
    set_bootstrap_env(monkeypatch, RUANGKAMPUS_BOOTSTRAP_ADMIN_PASSWORD="short")
    try:
        cli.create_admin_from_env()
    except SystemExit as exc:
        assert "at least 16 characters" in str(exc)
    else:
        raise AssertionError("Bootstrap must reject short passwords")
