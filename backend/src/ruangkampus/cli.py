import argparse
from getpass import getpass

from sqlalchemy import select

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
        existing = db.scalar(select(User.id).where(User.email == email))
        if existing:
            raise SystemExit("An account with that email already exists")
        user = User(name=name, email=email, password_hash=hash_password(password), role="TU_ADMIN", account_status="ACTIVE")
        db.add(user)
        db.commit()
        print(f"Administrator created: {email} (id={user.id})")
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="RuangKampus backend administration commands")
    parser.add_argument("command", choices=["create-admin"])
    args = parser.parse_args()
    if args.command == "create-admin":
        create_admin()


if __name__ == "__main__":
    main()
