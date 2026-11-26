from ruangkampus.models import Notification
from ruangkampus.routers.reservations import _notify_once


def test_notification_event_key_prevents_duplicate_in_app_events(db_session, student):
    first, first_created = _notify_once(
        db_session, student, "RESERVATION_APPROVED", "Approved", "Your room is approved.",
        "reservation:unique-test:approved:student",
    )
    db_session.commit()
    second, second_created = _notify_once(
        db_session, student, "RESERVATION_APPROVED", "Approved", "Your room is approved.",
        "reservation:unique-test:approved:student",
    )
    db_session.commit()
    assert first_created is True
    assert second_created is False
    assert first.id == second.id
    assert db_session.query(Notification).filter_by(event_key="reservation:unique-test:approved:student").count() == 1


def test_notifications_are_visible_only_to_recipient(client, auth_headers, student, db_session):
    notification = Notification(
        recipient_id=student.id,
        notification_type="TEST",
        title="Private update",
        message="Only the recipient should see this.",
    )
    db_session.add(notification)
    db_session.commit()

    second = client.post("/api/v1/auth/register", json={
        "name": "Second Student", "email": "second@example.com", "student_identifier": "2403045008", "password": "AnotherStrongPass123!"
    })
    assert second.status_code == 201
    second_headers = {"Authorization": f"Bearer {second.json()['access_token']}"}
    hidden = client.get("/api/v1/notifications", headers=second_headers)
    assert hidden.status_code == 200
    assert hidden.json()["data"] == []
    denied = client.patch(f"/api/v1/notifications/{notification.id}/read", headers=second_headers)
    assert denied.status_code == 404

    own_headers = auth_headers()
    visible = client.get("/api/v1/notifications?unreadOnly=true", headers=own_headers)
    assert visible.status_code == 200
    assert len(visible.json()["data"]) == 1
    marked = client.patch(f"/api/v1/notifications/{notification.id}/read", headers=own_headers)
    assert marked.status_code == 200
    assert marked.json()["data"]["read_at"] is not None


def test_student_cancellation_notifies_administrator_not_cancelled_student(client, auth_headers, student, admin, create_room, db_session):
    from datetime import date, timedelta

    room = create_room()
    today = date.today()
    booking_date = today + timedelta(days=7)
    while booking_date.weekday() == today.weekday():
        booking_date += timedelta(days=1)
    created = client.post("/api/v1/reservations", json={
        "room_id": room["id"], "purpose": "Cancellation notice test", "date": booking_date.isoformat(),
        "start_time": "12:00:00", "end_time": "13:00:00", "participant_count": 4,
    }, headers=auth_headers())
    assert created.status_code == 201, created.text
    reservation_id = created.json()["data"]["id"]
    response = client.patch(
        f"/api/v1/reservations/{reservation_id}/cancel",
        json={"reason": "Schedule changed"},
        headers=auth_headers(),
    )
    assert response.status_code == 200
    admin_notifications = db_session.query(Notification).filter_by(
        recipient_id=admin.id, notification_type="RESERVATION_CANCELLED_BY_STUDENT"
    ).count()
    student_notifications = db_session.query(Notification).filter_by(
        recipient_id=student.id, notification_type="RESERVATION_CANCELLED_BY_STUDENT"
    ).count()
    assert admin_notifications == 1
    assert student_notifications == 0



def test_transactional_reservation_emails_link_to_the_correct_role_pages(
    client, auth_headers, student, admin, create_room, monkeypatch
):
    from datetime import date, timedelta

    sent = []

    def fake_send_email(to_email, subject, body, html_body=None):
        sent.append({"to": to_email, "subject": subject, "body": body, "html": html_body})
        return True

    monkeypatch.setattr("ruangkampus.routers.reservations.send_email", fake_send_email)
    room = create_room()
    student_headers = auth_headers()
    admin_headers = auth_headers("admin.uhamka")
    base_date = date.today() + timedelta(days=14)

    def submit(offset: int) -> str:
        booking_date = base_date + timedelta(days=offset)
        response = client.post(
            "/api/v1/reservations",
            json={
                "room_id": room["id"],
                "purpose": "Email flow verification",
                "date": booking_date.isoformat(),
                "start_time": "12:00:00",
                "end_time": "13:00:00",
                "participant_count": 4,
            },
            headers=student_headers,
        )
        assert response.status_code == 201, response.text
        return response.json()["data"]["id"]

    first_id = submit(0)
    assert sent[0]["to"] == admin.email
    assert f"http://localhost:5173/admin/reservations/{first_id}" in sent[0]["body"]
    assert f'href="http://localhost:5173/admin/reservations/{first_id}"' in sent[0]["html"]
    assert "Nama pemohon" in sent[0]["html"]

    approved = client.patch(f"/api/v1/reservations/{first_id}/approve", headers=admin_headers)
    assert approved.status_code == 200, approved.text
    assert sent[1]["to"] == student.email
    assert f"http://localhost:5173/student/reservations/{first_id}" in sent[1]["body"]
    assert f'href="http://localhost:5173/student/reservations/{first_id}"' in sent[1]["html"]

    second_id = submit(1)
    rejected = client.patch(
        f"/api/v1/reservations/{second_id}/reject",
        json={"rejection_reason": "Ruangan dipakai untuk kegiatan fakultas"},
        headers=admin_headers,
    )
    assert rejected.status_code == 200, rejected.text
    assert sent[3]["to"] == student.email
    assert "Ruangan dipakai untuk kegiatan fakultas" in sent[3]["html"]
    assert f"/student/reservations/{second_id}" in sent[3]["body"]

    third_id = submit(2)
    cancelled_by_student = client.patch(
        f"/api/v1/reservations/{third_id}/cancel",
        json={"reason": "Jadwal berubah"},
        headers=student_headers,
    )
    assert cancelled_by_student.status_code == 200, cancelled_by_student.text
    assert sent[5]["to"] == admin.email
    assert f"http://localhost:5173/admin/reservations/{third_id}" in sent[5]["body"]
    assert "Jadwal berubah" in sent[5]["html"]

    fourth_id = submit(3)
    cancelled_by_admin = client.patch(
        f"/api/v1/reservations/{fourth_id}/cancel",
        json={"reason": "Penyesuaian operasional"},
        headers=admin_headers,
    )
    assert cancelled_by_admin.status_code == 200, cancelled_by_admin.text
    assert sent[7]["to"] == student.email
    assert f"http://localhost:5173/student/reservations/{fourth_id}" in sent[7]["body"]
