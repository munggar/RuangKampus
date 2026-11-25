import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from ruangkampus.database import Base, get_db
from ruangkampus.main import app
from ruangkampus.models import User
from ruangkampus.security import hash_password
from ruangkampus.rate_limit import limiter


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture()
def client(db_session):
    limiter._events.clear()
    def override_get_db():
        yield db_session
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def student(db_session):
    user = User(name="Student Test", email="student@example.com", student_identifier="2403045007", password_hash=hash_password("StrongPass123!"), role="STUDENT")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture()
def admin(db_session):
    user = User(name="Admin Test", email="admin@example.com", student_identifier="admin.uhamka", password_hash=hash_password("StrongPass123!"), role="TU_ADMIN")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture()
def auth_headers(client):
    def login(identifier="2403045007", password="StrongPass123!"):
        response = client.post("/api/v1/auth/login", json={"identifier": identifier, "password": password})
        assert response.status_code == 200, response.text
        return {"Authorization": f"Bearer {response.json()['access_token']}"}
    return login


@pytest.fixture()
def room_payload():
    return {
        "room_name": "Room 101",
        "room_code": "R-101",
        "building": "Building A",
        "floor": "1",
        "capacity": 30,
        "facilities": ["Projector", "Whiteboard"],
        "operating_hours": {"monday": [{"start": "07:00:00", "end": "21:00:00"}], "tuesday": [{"start": "07:00:00", "end": "21:00:00"}], "wednesday": [{"start": "07:00:00", "end": "21:00:00"}], "thursday": [{"start": "07:00:00", "end": "21:00:00"}], "friday": [{"start": "07:00:00", "end": "21:00:00"}], "saturday": [{"start": "07:00:00", "end": "21:00:00"}], "sunday": [{"start": "07:00:00", "end": "21:00:00"}]},
    }


@pytest.fixture()
def create_room(client, auth_headers, room_payload):
    def create():
        admin_headers = auth_headers("admin.uhamka")
        response = client.post("/api/v1/rooms", json=room_payload, headers=admin_headers)
        assert response.status_code == 201, response.text
        return response.json()["data"]
    return create
