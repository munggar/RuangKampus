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


def test_notifications_are_visible_only_to_recipient(client, auth_headers, student, admin, db_session):
    notification = Notification(
        recipient_id=student.id,
        notification_type="TEST",
        title="Private update",
        message="Only the recipient should see this.",
    )
    db_session.add(notification)
    db_session.commit()

    second = client.post("/api/v1/users", headers=auth_headers("admin.uhamka"), json={
        "name": "Second Student", "email": "second@example.com",
        "student_identifier": "2403045008", "password": "AnotherStrongPass123!"
    })
    assert second.status_code == 201, second.text
    second_login = client.post("/api/v1/auth/login", json={
        "identifier": "2403045008", "password": "AnotherStrongPass123!"
    })
    assert second_login.status_code == 200, second_login.text
    second_headers = {"Authorization": f"Bearer {second_login.json()['access_token']}"}
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
