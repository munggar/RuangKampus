from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from ruangkampus.config import get_settings
from ruangkampus.database import SessionLocal, engine, get_db
from ruangkampus.main import app
from ruangkampus.models import Room, User
from ruangkampus.rate_limit import limiter
from ruangkampus.security import hash_password


@pytest.fixture(scope="session")
def postgres_engine():
    if engine.dialect.name != "postgresql":
        pytest.skip("PostgreSQL integration suite requires DATABASE_URL to use PostgreSQL")
    yield engine


@pytest.fixture(autouse=True)
def clean_postgres_database(postgres_engine):
    # CI points this engine at a dedicated disposable integration database.
    with postgres_engine.begin() as connection:
        connection.execute(text("TRUNCATE TABLE rooms, users CASCADE"))
    limiter._events.clear()
    yield


@pytest.fixture()
def pg_session(postgres_engine):
    session: Session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def pg_client():
    def override_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture()
def pg_users(pg_session):
    admin = User(
        name="Postgres Admin",
        email="pg-admin@example.com",
        password_hash=hash_password("StrongPass123!"),
        role="TU_ADMIN",
    )
    student_a = User(
        name="Postgres Student A",
        email="pg-a@example.com",
        password_hash=hash_password("StrongPass123!"),
        role="STUDENT",
    )
    student_b = User(
        name="Postgres Student B",
        email="pg-b@example.com",
        password_hash=hash_password("StrongPass123!"),
        role="STUDENT",
    )
    pg_session.add_all([admin, student_a, student_b])
    pg_session.commit()
    pg_session.refresh(admin)
    pg_session.refresh(student_a)
    pg_session.refresh(student_b)
    return {"admin": admin, "student_a": student_a, "student_b": student_b}


@pytest.fixture()
def pg_room(pg_session):
    hours = {
        day: [{"start": "07:00:00", "end": "21:00:00"}]
        for day in ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
    }
    room = Room(
        room_name="Postgres Test Room",
        room_code="PG-R-01",
        building="Integration Building",
        capacity=40,
        facilities=["Projector", "Whiteboard"],
        operating_hours=hours,
        room_status="ACTIVE",
    )
    pg_session.add(room)
    pg_session.commit()
    pg_session.refresh(room)
    return room


@pytest.fixture()
def pg_tokens(pg_client, pg_users):
    headers = {}
    for key, user in pg_users.items():
        result = pg_client.post("/api/v1/auth/login", json={
            "email": user.email,
            "password": "StrongPass123!",
        })
        assert result.status_code == 200, result.text
        headers[key] = {"Authorization": f"Bearer {result.json()['access_token']}"}
    return headers


@pytest.fixture()
def future_booking_date() -> date:
    today = datetime.now(ZoneInfo(get_settings().campus_timezone)).date()
    days = (4 - today.weekday()) % 7
    return today + timedelta(days=days if days >= 2 else days + 7)
