from datetime import date, timedelta
import os
from pathlib import Path


def next_weekday(weekday: int) -> date:
    today = date.today()
    days = (weekday - today.weekday()) % 7
    days = days if days >= 2 else days + 7
    return today + timedelta(days=days)


def test_refresh_token_rotation_and_logout(client, student):
    login = client.post("/api/v1/auth/login", json={"identifier": "2403045007", "password": "StrongPass123!"})
    assert login.status_code == 200
    old_refresh = client.cookies.get("ruangkampus_refresh")
    refreshed = client.post("/api/v1/auth/refresh")
    assert refreshed.status_code == 200, refreshed.text
    new_refresh = client.cookies.get("ruangkampus_refresh")
    assert old_refresh and new_refresh and new_refresh != old_refresh
    headers = {"Authorization": f"Bearer {refreshed.json()['access_token']}"}
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 200
    logout = client.post("/api/v1/auth/logout", headers=headers)
    assert logout.status_code == 200
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 401


def test_password_reset_token_is_one_time_and_revokes_sessions(client, student):
    old_headers_response = client.post("/api/v1/auth/login", json={"identifier": "2403045007", "password": "StrongPass123!"})
    old_headers = {"Authorization": f"Bearer {old_headers_response.json()['access_token']}"}

    mailbox = Path(os.environ.get("LOCAL_MAILBOX_DIR", ".local_mailbox"))
    mailbox.mkdir(exist_ok=True)
    for old_file in mailbox.glob("*.eml.txt"):
        old_file.unlink()

    forgot = client.post("/api/v1/auth/forgot-password", json={"email": "student@example.com"})
    assert forgot.status_code == 202
    assert "token" not in forgot.text.lower()
    mail_files = list(mailbox.glob("*.eml.txt"))
    assert len(mail_files) == 1
    message = mail_files[0].read_text(encoding="utf-8")
    token = message.split("token=", 1)[1].split()[0]

    reset = client.post("/api/v1/auth/reset-password", json={"token": token, "new_password": "AnotherStrongPass456!"})
    assert reset.status_code == 200, reset.text
    assert client.get("/api/v1/auth/me", headers=old_headers).status_code == 401

    replay = client.post("/api/v1/auth/reset-password", json={"token": token, "new_password": "ThirdStrongPass789!"})
    assert replay.status_code == 400
    new_login = client.post("/api/v1/auth/login", json={"identifier": "2403045007", "password": "AnotherStrongPass456!"})
    assert new_login.status_code == 200
    assert new_login.json()["user"]["role"] == "Student"


def test_dashboard_counts_from_database(client, auth_headers, student, admin, create_room):
    room = create_room()
    booking_date = next_weekday(4)
    response = client.post("/api/v1/reservations", json={
        "room_id": room["id"],
        "purpose": "Dashboard test",
        "date": booking_date.isoformat(),
        "start_time": "15:00:00",
        "end_time": "16:00:00",
        "participant_count": 5,
    }, headers=auth_headers())
    assert response.status_code == 201
    student_summary = client.get("/api/v1/dashboard/summary", headers=auth_headers())
    assert student_summary.status_code == 200
    assert student_summary.json()["data"]["total_reservations"] == 1
    admin_summary = client.get("/api/v1/dashboard/summary", headers=auth_headers("admin.uhamka"))
    assert admin_summary.status_code == 200
    assert admin_summary.json()["data"]["total_rooms"] == 1
    assert admin_summary.json()["data"]["pending"] == 1


def test_student_cannot_see_another_students_reservation(client, auth_headers, student, admin, create_room):
    room = create_room()
    booking_date = next_weekday(5)
    created = client.post("/api/v1/reservations", json={
        "room_id": room["id"], "purpose": "Private meeting", "date": booking_date.isoformat(),
        "start_time": "17:00:00", "end_time": "18:00:00", "participant_count": 3,
    }, headers=auth_headers())
    reservation_id = created.json()["data"]["id"]

    second_student = client.post("/api/v1/auth/register", json={
        "name": "Another Student", "email": "other.student@example.com", "student_identifier": "2403045009", "password": "VeryStrongPass456!"
    })
    assert second_student.status_code == 201
    second_headers = {"Authorization": f"Bearer {second_student.json()['access_token']}"}
    hidden = client.get(f"/api/v1/reservations/{reservation_id}", headers=second_headers)
    assert hidden.status_code == 404
    history = client.get("/api/v1/reservations", headers=second_headers)
    assert history.status_code == 200
    assert history.json()["data"] == []
