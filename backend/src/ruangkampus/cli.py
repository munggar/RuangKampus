import argparse
import os
from getpass import getpass

from pydantic import EmailStr, TypeAdapter, ValidationError
from sqlalchemy import func, select

from ruangkampus.database import SessionLocal
from ruangkampus.models import User
from ruangkampus.security import hash_password


def create_admin():
    email = input("Admin email: ").strip().lower()
    name = input("Admin full name: ").strip()
    password = getpass("Temporary password (10+ characters): ")
    confirm = getpass("Confirm password: ")
    if password != confirm or len(password) < 10:
        raise SystemExit("Passwords do not match or are too short")
    db = SessionLocal()
    try:
        existing = db.scalar(select(User.id).where((User.email == email) | (User.student_identifier == "admin.uhamka")))
        if existing:
            raise SystemExit("An account with that email or administrator username already exists")
        user = User(name=name, email=email, student_identifier="admin.uhamka", password_hash=hash_password(password), role="TU_ADMIN", account_status="ACTIVE")
        db.add(user)
        db.commit()
        print(f"Administrator created: {email} (id={user.id})")
    finally:
        db.close()


def create_admin_from_env():
    """One-time bootstrap for an empty installation; never exposed through HTTP."""
    # Email stays required by the user record, but authentication uses the
    # reserved username. The .invalid address is deliberately non-deliverable.
    email_value = os.environ.get("RUANGKAMPUS_BOOTSTRAP_ADMIN_EMAIL", "admin.uhamka@example.com").strip().lower()
    name = os.environ.get("RUANGKAMPUS_BOOTSTRAP_ADMIN_NAME", "Admin UHAMKA").strip()
    password = os.environ.get("RUANGKAMPUS_BOOTSTRAP_ADMIN_PASSWORD", "")
    username = "admin.uhamka"
    if not name or len(password) < 16:
        raise SystemExit("Bootstrap requires a name and a password of at least 16 characters")
    if len(name) < 2 or len(name) > 160:
        raise SystemExit("Bootstrap administrator name must contain 2 to 160 characters")
    try:
        email = str(TypeAdapter(EmailStr).validate_python(email_value))
    except ValidationError:
        raise SystemExit("Bootstrap administrator email is invalid") from None

    db = SessionLocal()
    try:
        existing_by_username = db.scalar(select(User).where(func.lower(User.student_identifier) == username))
        existing_by_email = db.scalar(select(User).where(func.lower(User.email) == email.lower()))
        existing = existing_by_username or existing_by_email
        if existing is not None:
            if existing.role == "TU_ADMIN" and existing.account_status == "ACTIVE" and existing.deleted_at is None:
                if existing.email.lower() != email.lower():
                    raise SystemExit("Bootstrap is restricted to an installation without a different active TU/Admin account")
                if existing.student_identifier not in (None, username):
                    raise SystemExit("An active administrator already uses a different login username")
                if existing.student_identifier is None:
                    existing.student_identifier = username
                    db.commit()
                print(f"Bootstrap administrator already exists: {username}")
                return
            raise SystemExit("The bootstrap email or username is already assigned to a non-administrator account")

        admin_count = db.scalar(select(func.count()).select_from(User).where(
            User.role == "TU_ADMIN",
            User.account_status == "ACTIVE",
            User.deleted_at.is_(None),
        )) or 0
        if admin_count:
            raise SystemExit("Bootstrap is restricted to an installation without an active TU/Admin account")

        user = User(
            name=name,
            email=email,
            student_identifier=username,
            password_hash=hash_password(password),
            role="TU_ADMIN",
            account_status="ACTIVE",
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        # Never print or log the bootstrap password.
        print(f"Bootstrap administrator created: {username} (id={user.id})")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="RuangKampus backend administration commands")
    parser.add_argument("command", choices=["create-admin", "create-admin-from-env"])
    args = parser.parse_args()
    if args.command == "create-admin":
        create_admin()
    elif args.command == "create-admin-from-env":
        create_admin_from_env()


if __name__ == "__main__":
    main()
