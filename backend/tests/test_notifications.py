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


def test_mark_all_read_updates_only_the_authenticated_recipient(client, auth_headers, student, admin, db_session):
    from ruangkampus.models import utcnow

    unread_first = Notification(
        recipient_id=student.id,
        notification_type="RESERVATION_APPROVED",
        title="Reservasi disetujui",
        message="Reservasi pertama disetujui.",
        action_url="/student/reservations/first",
    )
    unread_second = Notification(
        recipient_id=student.id,
        notification_type="RESERVATION_REJECTED",
        title="Reservasi ditolak",
        message="Reservasi kedua ditolak.",
    )
    already_read = Notification(
        recipient_id=student.id,
        notification_type="RESERVATION_NEW",
        title="Pemberitahuan lama",
        message="Sudah dibaca.",
        read_at=utcnow(),
    )
    admin_unread = Notification(
        recipient_id=admin.id,
        notification_type="RESERVATION_NEW",
        title="Permohonan baru",
        message="Tetap belum dibaca oleh admin.",
    )
    db_session.add_all([unread_first, unread_second, already_read, admin_unread])
    db_session.commit()

    headers = auth_headers()
    response = client.patch("/api/v1/notifications/read-all", headers=headers)
    assert response.status_code == 200, response.text
    assert response.json()["data"]["updated_count"] == 2

    listed = client.get("/api/v1/notifications?unreadOnly=true", headers=headers)
    assert listed.status_code == 200
    assert listed.json()["data"] == []

    admin_unread_response = client.get(
        "/api/v1/notifications?unreadOnly=true",
        headers=auth_headers("admin.uhamka"),
    )
    assert admin_unread_response.status_code == 200
    assert len(admin_unread_response.json()["data"]) == 1

    all_notifications = client.get("/api/v1/notifications?page=1&limit=20", headers=headers)
    action_notification = next(item for item in all_notifications.json()["data"] if item["id"] == str(unread_first.id))
    assert action_notification["action_url"] == "/student/reservations/first"


def test_admin_can_retry_only_failed_notification_email_with_attempt_limit(
    client, auth_headers, student, db_session, monkeypatch
):
    sent = []

    def fake_send_email(to_email, subject, body, html_body=None):
        sent.append({"to": to_email, "subject": subject, "body": body, "html": html_body})
        return True

    monkeypatch.setattr("ruangkampus.routers.notifications.send_email", fake_send_email)
    failed = Notification(
        recipient_id=student.id,
        notification_type="RESERVATION_APPROVED",
        title="Reservasi disetujui",
        message="Reservasi ruang telah disetujui.",
        action_url="/student/reservations/retry-test",
        email_delivery_status="FAILED",
        email_attempt_count=1,
    )
    exhausted = Notification(
        recipient_id=student.id,
        notification_type="RESERVATION_REJECTED",
        title="Reservasi ditolak",
        message="Percobaan email telah mencapai batas.",
        email_delivery_status="FAILED",
        email_attempt_count=3,
    )
    db_session.add_all([failed, exhausted])
    db_session.commit()

    admin_headers = auth_headers("admin.uhamka")
    retried = client.post(
        f"/api/v1/notifications/{failed.id}/retry-email",
        headers=admin_headers,
    )
    assert retried.status_code == 200, retried.text
    result = retried.json()["data"]
    assert result["email_attempt_count"] == 2
    assert result["email_delivery_status"] in {"SENT", "LOCAL_MAILBOX_WRITTEN"}
    assert sent[0]["to"] == student.email
    assert "/student/reservations/retry-test" in sent[0]["body"]
    assert "action" in sent[0]["html"].lower() or "reservasi" in sent[0]["html"].lower()

    not_failed = client.post(
        f"/api/v1/notifications/{failed.id}/retry-email",
        headers=admin_headers,
    )
    assert not_failed.status_code == 409
    limit_reached = client.post(
        f"/api/v1/notifications/{exhausted.id}/retry-email",
        headers=admin_headers,
    )
    assert limit_reached.status_code == 409


def test_completion_creates_an_in_app_notification_and_transactional_email(
    client, auth_headers, student, admin, create_room, db_session, monkeypatch
):
    from datetime import date, timedelta
    from uuid import UUID
    from ruangkampus.models import Reservation

    sent = []
    monkeypatch.setattr(
        "ruangkampus.routers.reservations.send_email",
        lambda to_email, subject, body, html_body=None: sent.append((to_email, subject, body, html_body)) or True,
    )

    room = create_room()
    booking_date = date.today() + timedelta(days=8)
    student_headers = auth_headers()
    admin_headers = auth_headers("admin.uhamka")
    created = client.post("/api/v1/reservations", json={
        "room_id": room["id"],
        "purpose": "Completion notification test",
        "date": booking_date.isoformat(),
        "start_time": "12:00:00",
        "end_time": "13:00:00",
        "participant_count": 4,
    }, headers=student_headers)
    assert created.status_code == 201, created.text
    reservation_id = created.json()["data"]["id"]

    approved = client.patch(f"/api/v1/reservations/{reservation_id}/approve", headers=admin_headers)
    assert approved.status_code == 200, approved.text

    reservation = db_session.get(Reservation, UUID(reservation_id))
    reservation.reservation_date = date.today() - timedelta(days=1)
    db_session.commit()

    completed = client.patch(f"/api/v1/reservations/{reservation_id}/complete", headers=admin_headers)
    assert completed.status_code == 200, completed.text

    notification = db_session.query(Notification).filter_by(
        recipient_id=student.id,
        notification_type="RESERVATION_COMPLETED",
    ).one()
    assert notification.action_url == f"/student/reservations/{reservation_id}"
    assert notification.title == "Reservasi selesai"
    assert "ditandai selesai" in notification.message
    assert sent[-1][0] == student.email
    assert "Reservasi selesai" in sent[-1][1]


def test_mark_all_read_updates_only_the_authenticated_recipient(client, auth_headers, student, admin, db_session):
    from ruangkampus.models import utcnow

    unread_first = Notification(
        recipient_id=student.id,
        notification_type="RESERVATION_APPROVED",
        title="Reservasi disetujui",
        message="Reservasi pertama disetujui.",
        action_url="/student/reservations/first",
    )
    unread_second = Notification(
        recipient_id=student.id,
        notification_type="RESERVATION_REJECTED",
        title="Reservasi ditolak",
        message="Reservasi kedua ditolak.",
    )
    already_read = Notification(
        recipient_id=student.id,
        notification_type="RESERVATION_NEW",
        title="Pemberitahuan lama",
        message="Sudah dibaca.",
        read_at=utcnow(),
    )
    admin_unread = Notification(
        recipient_id=admin.id,
        notification_type="RESERVATION_NEW",
        title="Permohonan baru",
        message="Tetap belum dibaca oleh admin.",
    )
    db_session.add_all([unread_first, unread_second, already_read, admin_unread])
    db_session.commit()

    headers = auth_headers()
    response = client.patch("/api/v1/notifications/read-all", headers=headers)
    assert response.status_code == 200, response.text
    assert response.json()["data"]["updated_count"] == 2

    listed = client.get("/api/v1/notifications?unreadOnly=true", headers=headers)
    assert listed.status_code == 200
    assert listed.json()["data"] == []

    admin_unread_response = client.get(
        "/api/v1/notifications?unreadOnly=true",
        headers=auth_headers("admin.uhamka"),
    )
    assert admin_unread_response.status_code == 200
    assert len(admin_unread_response.json()["data"]) == 1

    all_notifications = client.get("/api/v1/notifications?page=1&limit=20", headers=headers)
    action_notification = next(item for item in all_notifications.json()["data"] if item["id"] == str(unread_first.id))
    assert action_notification["action_url"] == "/student/reservations/first"


def test_notification_list_paginates_and_preserves_unread_total(client, auth_headers, student, db_session):
    for index in range(3):
        db_session.add(Notification(
            recipient_id=student.id,
            notification_type="TEST",
            title=f"Notifikasi {index}",
            message=f"Isi notifikasi {index}",
        ))
    db_session.commit()

    first_page = client.get("/api/v1/notifications?page=1&limit=2", headers=auth_headers())
    second_page = client.get("/api/v1/notifications?page=2&limit=2", headers=auth_headers())
    assert first_page.status_code == 200
    assert len(first_page.json()["data"]) == 2
    assert first_page.json()["meta"]["total"] == 3
    assert first_page.json()["meta"]["total_pages"] == 2
    assert second_page.status_code == 200
    assert len(second_page.json()["data"]) == 1


def test_admin_can_retry_only_failed_notification_email_with_attempt_limit(
    client, auth_headers, student, db_session, monkeypatch
):
    sent = []

    def fake_send_email(to_email, subject, body, html_body=None):
        sent.append({"to": to_email, "subject": subject, "body": body, "html": html_body})
        return True

    monkeypatch.setattr("ruangkampus.routers.notifications.send_email", fake_send_email)
    failed = Notification(
        recipient_id=student.id,
        notification_type="RESERVATION_APPROVED",
        title="Reservasi disetujui",
        message="Reservasi ruang telah disetujui.",
        action_url="/student/reservations/retry-test",
        email_delivery_status="FAILED",
        email_attempt_count=1,
    )
    exhausted = Notification(
        recipient_id=student.id,
        notification_type="RESERVATION_REJECTED",
        title="Reservasi ditolak",
        message="Percobaan email telah mencapai batas.",
        email_delivery_status="FAILED",
        email_attempt_count=3,
    )
    db_session.add_all([failed, exhausted])
    db_session.commit()

    admin_headers = auth_headers("admin.uhamka")
    retried = client.post(
        f"/api/v1/notifications/{failed.id}/retry-email",
        headers=admin_headers,
    )
    assert retried.status_code == 200, retried.text
    result = retried.json()["data"]
    assert result["email_attempt_count"] == 2
    assert result["email_delivery_status"] in {"SENT", "LOCAL_MAILBOX_WRITTEN"}
    assert sent[0]["to"] == student.email
    assert "/student/reservations/retry-test" in sent[0]["body"]
    assert "reservasi" in sent[0]["html"].lower()

    not_failed = client.post(
        f"/api/v1/notifications/{failed.id}/retry-email",
        headers=admin_headers,
    )
    assert not_failed.status_code == 409
    limit_reached = client.post(
        f"/api/v1/notifications/{exhausted.id}/retry-email",
        headers=admin_headers,
    )
    assert limit_reached.status_code == 409


def test_completion_creates_an_in_app_notification_and_transactional_email(
    client, auth_headers, student, admin, create_room, db_session, monkeypatch
):
    from datetime import date, timedelta
    from uuid import UUID
    from ruangkampus.models import Reservation

    sent = []
    monkeypatch.setattr(
        "ruangkampus.routers.reservations.send_email",
        lambda to_email, subject, body, html_body=None: sent.append((to_email, subject, body, html_body)) or True,
    )

    room = create_room()
    booking_date = date.today() + timedelta(days=8)
    student_headers = auth_headers()
    admin_headers = auth_headers("admin.uhamka")
    created = client.post("/api/v1/reservations", json={
        "room_id": room["id"],
        "purpose": "Completion notification test",
        "date": booking_date.isoformat(),
        "start_time": "12:00:00",
        "end_time": "13:00:00",
        "participant_count": 4,
    }, headers=student_headers)
    assert created.status_code == 201, created.text
    reservation_id = created.json()["data"]["id"]

    approved = client.patch(f"/api/v1/reservations/{reservation_id}/approve", headers=admin_headers)
    assert approved.status_code == 200, approved.text

    reservation = db_session.get(Reservation, UUID(reservation_id))
    reservation.reservation_date = date.today() - timedelta(days=1)
    db_session.commit()

    completed = client.patch(f"/api/v1/reservations/{reservation_id}/complete", headers=admin_headers)
    assert completed.status_code == 200, completed.text

    notification = db_session.query(Notification).filter_by(
        recipient_id=student.id,
        notification_type="RESERVATION_COMPLETED",
    ).one()
    assert notification.action_url == f"/student/reservations/{reservation_id}"
    assert notification.title == "Reservasi selesai"
    assert "ditandai selesai" in notification.message
    assert sent[-1][0] == student.email
    assert "Reservasi selesai" in sent[-1][1]
