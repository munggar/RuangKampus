from datetime import date, timedelta


def next_weekday(weekday: int) -> date:
    today = date.today()
    days = (weekday - today.weekday()) % 7
    days = days if days >= 2 else days + 7
    return today + timedelta(days=days)


def test_student_cannot_create_room(client, auth_headers, room_payload, student, admin):
    response = client.post("/api/v1/rooms", json=room_payload, headers=auth_headers())
    assert response.status_code == 403


def test_admin_creates_room_and_filters(client, auth_headers, admin, room_payload):
    created = client.post("/api/v1/rooms", json=room_payload, headers=auth_headers("admin@example.com"))
    assert created.status_code == 201, created.text
    listed = client.get("/api/v1/rooms?building=Building%20A&min_capacity=20")
    assert listed.status_code == 200
    assert listed.json()["meta"]["total"] == 1


def test_pending_reservation_blocks_overlapping_request(client, db_session, auth_headers, student, admin, create_room):
    room = create_room()
    headers = auth_headers()
    booking_date = next_weekday(0)
    payload = {"room_id": room["id"], "purpose": "Study group", "date": booking_date.isoformat(), "start_time": "09:00:00", "end_time": "10:00:00", "participant_count": 5}
    first = client.post("/api/v1/reservations", json=payload, headers=headers)
    assert first.status_code == 201, first.text
    second_payload = {**payload, "start_time": "09:30:00", "end_time": "10:30:00"}
    second = client.post("/api/v1/reservations", json=second_payload, headers=headers)
    assert second.status_code == 409


def test_lecture_schedule_blocks_reservation(client, db_session, auth_headers, student, admin, create_room):
    room = create_room()
    admin_headers = auth_headers("admin@example.com")
    booking_date = next_weekday(0)
    schedule = client.post("/api/v1/admin/schedules", json={"room_id": room["id"], "course_name": "Test class", "schedule_date": booking_date.isoformat(), "start_time": "09:00:00", "end_time": "11:00:00", "data_source": "TEST_ONLY"}, headers=admin_headers)
    assert schedule.status_code == 201, schedule.text
    response = client.post("/api/v1/reservations", json={"room_id": room["id"], "purpose": "Meeting", "date": booking_date.isoformat(), "start_time": "09:30:00", "end_time": "10:30:00", "participant_count": 4}, headers=auth_headers())
    assert response.status_code == 409


def test_reservation_approval_and_student_data_isolation(client, auth_headers, student, admin, create_room, db_session):
    room = create_room()
    booking_date = next_weekday(1)
    request = client.post("/api/v1/reservations", json={"room_id": room["id"], "purpose": "Workshop", "date": booking_date.isoformat(), "start_time": "13:00:00", "end_time": "14:00:00", "participant_count": 10}, headers=auth_headers())
    assert request.status_code == 201
    reservation_id = request.json()["data"]["id"]
    assert client.get(f"/api/v1/reservations/{reservation_id}", headers=auth_headers("admin@example.com")).status_code == 200
    approved = client.patch(f"/api/v1/reservations/{reservation_id}/approve", headers=auth_headers("admin@example.com"))
    assert approved.status_code == 200, approved.text
    assert approved.json()["data"]["status"] == "APPROVED"


def test_student_cannot_approve_reservation(client, auth_headers, student, admin, create_room):
    room = create_room()
    booking_date = next_weekday(2)
    request = client.post("/api/v1/reservations", json={"room_id": room["id"], "purpose": "Workshop", "date": booking_date.isoformat(), "start_time": "13:00:00", "end_time": "14:00:00", "participant_count": 10}, headers=auth_headers())
    reservation_id = request.json()["data"]["id"]
    denied = client.patch(f"/api/v1/reservations/{reservation_id}/approve", headers=auth_headers())
    assert denied.status_code == 403


def test_over_capacity_and_non_future_rejected(client, auth_headers, student, admin, create_room):
    room = create_room()
    booking_date = next_weekday(3)
    oversized = client.post("/api/v1/reservations", json={"room_id": room["id"], "purpose": "Big event", "date": booking_date.isoformat(), "start_time": "13:00:00", "end_time": "14:00:00", "participant_count": 31}, headers=auth_headers())
    assert oversized.status_code == 409


def test_facility_filter_returns_matching_room(client, auth_headers, admin, create_room):
    create_room()
    matched = client.get("/api/v1/rooms?facilities=Projector")
    unmatched = client.get("/api/v1/rooms?facilities=3D%20Printer")
    assert matched.status_code == 200, matched.text
    assert matched.json()["meta"]["total"] == 1
    assert unmatched.json()["meta"]["total"] == 0


def test_student_can_cancel_only_own_pending_reservation(client, auth_headers, student, admin, create_room):
    room = create_room()
    booking_date = next_weekday(6)
    created = client.post("/api/v1/reservations", json={"room_id": room["id"], "purpose": "Cancel test", "date": booking_date.isoformat(), "start_time": "12:00:00", "end_time": "13:00:00", "participant_count": 2}, headers=auth_headers())
    assert created.status_code == 201
    reservation_id = created.json()["data"]["id"]
    cancelled = client.patch(f"/api/v1/reservations/{reservation_id}/cancel", json={"reason": "No longer needed"}, headers=auth_headers())
    assert cancelled.status_code == 200, cancelled.text
    assert cancelled.json()["data"]["status"] == "CANCELLED"


def test_schedule_creation_rejects_reservation_conflict(client, auth_headers, student, admin, create_room):
    room = create_room()
    booking_date = next_weekday(0)
    request = client.post("/api/v1/reservations", json={"room_id": room["id"], "purpose": "Exam prep", "date": booking_date.isoformat(), "start_time": "09:00:00", "end_time": "10:00:00", "participant_count": 6}, headers=auth_headers())
    assert request.status_code == 201
    response = client.post("/api/v1/admin/schedules", json={"room_id": room["id"], "course_name": "New class", "schedule_date": booking_date.isoformat(), "start_time": "09:30:00", "end_time": "10:30:00", "data_source": "TEST_ONLY"}, headers=auth_headers("admin@example.com"))
    assert response.status_code == 409


def test_user_admin_management_is_role_protected(client, auth_headers, student, admin):
    denied = client.get("/api/v1/users", headers=auth_headers())
    assert denied.status_code == 403
    listed = client.get("/api/v1/users?role=STUDENT", headers=auth_headers("admin@example.com"))
    assert listed.status_code == 200
    assert len(listed.json()["data"]) == 1
    updated = client.patch(f"/api/v1/users/{student.id}/status", json={"account_status": "DISABLED"}, headers=auth_headers("admin@example.com"))
    assert updated.status_code == 200
    assert updated.json()["data"]["account_status"] == "DISABLED"


def test_admin_cannot_deactivate_room_with_active_future_reservation(client, auth_headers, student, admin, create_room):
    room = create_room()
    booking_date = next_weekday(1)
    created = client.post("/api/v1/reservations", json={"room_id": room["id"], "purpose": "Reserved slot", "date": booking_date.isoformat(), "start_time": "11:00:00", "end_time": "12:00:00", "participant_count": 2}, headers=auth_headers())
    assert created.status_code == 201
    result = client.patch(f"/api/v1/rooms/{room['id']}", json={"room_status": "INACTIVE"}, headers=auth_headers("admin@example.com"))
    assert result.status_code == 409


def test_admin_activity_tracks_reservation_approval(client, auth_headers, student, admin, create_room):
    room = create_room()
    booking_date = next_weekday(0)
    created = client.post("/api/v1/reservations", json={"room_id": room["id"], "purpose": "Audit test", "date": booking_date.isoformat(), "start_time": "19:00:00", "end_time": "20:00:00", "participant_count": 3}, headers=auth_headers())
    reservation_id = created.json()["data"]["id"]
    approved = client.patch(f"/api/v1/reservations/{reservation_id}/approve", headers=auth_headers("admin@example.com"))
    assert approved.status_code == 200
    activity = client.get("/api/v1/admin/activity?entity_type=RESERVATION&action=APPROVE_RESERVATION", headers=auth_headers("admin@example.com"))
    assert activity.status_code == 200, activity.text
    assert activity.json()["meta"]["total"] == 1



def test_adjacent_pending_reservations_are_allowed(client, auth_headers, student, admin, create_room):
    room = create_room()
    booking_date = next_weekday(3)
    first = client.post("/api/v1/reservations", json={
        "room_id": room["id"], "purpose": "Morning class", "date": booking_date.isoformat(),
        "start_time": "09:00:00", "end_time": "10:00:00", "participant_count": 12,
    }, headers=auth_headers())
    second = client.post("/api/v1/reservations", json={
        "room_id": room["id"], "purpose": "Following class", "date": booking_date.isoformat(),
        "start_time": "10:00:00", "end_time": "11:00:00", "participant_count": 12,
    }, headers=auth_headers())
    assert first.status_code == 201, first.text
    assert second.status_code == 201, second.text


def test_approved_reservation_still_blocks_overlapping_request(client, auth_headers, student, admin, create_room):
    room = create_room()
    booking_date = next_weekday(4)
    created = client.post("/api/v1/reservations", json={
        "room_id": room["id"], "purpose": "Approved blocker", "date": booking_date.isoformat(),
        "start_time": "09:00:00", "end_time": "11:00:00", "participant_count": 4,
    }, headers=auth_headers())
    reservation_id = created.json()["data"]["id"]
    approved = client.patch(f"/api/v1/reservations/{reservation_id}/approve", headers=auth_headers("admin@example.com"))
    assert approved.status_code == 200
    blocked = client.post("/api/v1/reservations", json={
        "room_id": room["id"], "purpose": "Overlapping request", "date": booking_date.isoformat(),
        "start_time": "10:00:00", "end_time": "12:00:00", "participant_count": 4,
    }, headers=auth_headers())
    assert blocked.status_code == 409


def test_rejected_reservation_does_not_block_reuse(client, auth_headers, student, admin, create_room):
    room = create_room()
    booking_date = next_weekday(5)
    created = client.post("/api/v1/reservations", json={
        "room_id": room["id"], "purpose": "Reject this", "date": booking_date.isoformat(),
        "start_time": "09:00:00", "end_time": "10:00:00", "participant_count": 4,
    }, headers=auth_headers())
    reservation_id = created.json()["data"]["id"]
    rejected = client.patch(
        f"/api/v1/reservations/{reservation_id}/reject",
        json={"rejection_reason": "Room priority changed"},
        headers=auth_headers("admin@example.com"),
    )
    assert rejected.status_code == 200
    reused = client.post("/api/v1/reservations", json={
        "room_id": room["id"], "purpose": "Replacement request", "date": booking_date.isoformat(),
        "start_time": "09:00:00", "end_time": "10:00:00", "participant_count": 4,
    }, headers=auth_headers())
    assert reused.status_code == 201, reused.text


def test_cancelled_reservation_does_not_block_reuse(client, auth_headers, student, admin, create_room):
    room = create_room()
    booking_date = next_weekday(6)
    created = client.post("/api/v1/reservations", json={
        "room_id": room["id"], "purpose": "Cancel this", "date": booking_date.isoformat(),
        "start_time": "09:00:00", "end_time": "10:00:00", "participant_count": 4,
    }, headers=auth_headers())
    reservation_id = created.json()["data"]["id"]
    cancelled = client.patch(
        f"/api/v1/reservations/{reservation_id}/cancel",
        json={"reason": "No longer needed"},
        headers=auth_headers(),
    )
    assert cancelled.status_code == 200
    reused = client.post("/api/v1/reservations", json={
        "room_id": room["id"], "purpose": "Replacement booking", "date": booking_date.isoformat(),
        "start_time": "09:00:00", "end_time": "10:00:00", "participant_count": 4,
    }, headers=auth_headers())
    assert reused.status_code == 201, reused.text


def test_room_availability_reports_maintenance_inactive_and_hours(client, auth_headers, student, admin, create_room):
    room = create_room()
    booking_date = next_weekday(0)
    outside = client.get(
        f"/api/v1/rooms/{room['id']}/availability?date={booking_date.isoformat()}&startTime=22:00&endTime=23:00&participantCount=2"
    )
    assert outside.status_code == 200
    assert "OUTSIDE_OPERATING_HOURS_OR_NOT_CONFIGURED" in outside.json()["data"]["reasons"]

    changed = client.patch(
        f"/api/v1/rooms/{room['id']}",
        json={"room_status": "MAINTENANCE"},
        headers=auth_headers("admin@example.com"),
    )
    assert changed.status_code == 200
    maintenance = client.get(
        f"/api/v1/rooms/{room['id']}/availability?date={booking_date.isoformat()}&startTime=12:00&endTime=13:00&participantCount=2"
    )
    assert "ROOM_IN_MAINTENANCE" in maintenance.json()["data"]["reasons"]


def test_maintenance_period_blocks_new_reservation(client, auth_headers, student, admin, create_room):
    room = create_room()
    booking_date = next_weekday(1)
    admin_headers = auth_headers("admin@example.com")
    block = client.post("/api/v1/admin/room-unavailability", json={
        "room_id": room["id"], "unavailable_date": booking_date.isoformat(),
        "start_time": "13:00:00", "end_time": "15:00:00", "reason": "Air conditioner maintenance",
    }, headers=admin_headers)
    assert block.status_code == 201, block.text
    reservation = client.post("/api/v1/reservations", json={
        "room_id": room["id"], "purpose": "Meeting", "date": booking_date.isoformat(),
        "start_time": "14:00:00", "end_time": "14:30:00", "participant_count": 3,
    }, headers=auth_headers())
    assert reservation.status_code == 409


def test_completed_reservation_is_historical_and_does_not_block(client, auth_headers, student, admin, create_room, db_session):
    from datetime import time
    from uuid import UUID

    from ruangkampus.models import Reservation

    room = create_room()
    booking_date = next_weekday(2)
    historical = Reservation(
        user_id=student.id, room_id=UUID(room["id"]),
        purpose="Historical reservation", reservation_date=booking_date,
        start_time=time(9, 0), end_time=time(10, 0),
        participant_count=5, status="COMPLETED",
    )
    db_session.add(historical)
    db_session.commit()
    request = client.post("/api/v1/reservations", json={
        "room_id": room["id"], "purpose": "New slot request", "date": booking_date.isoformat(),
        "start_time": "09:00:00", "end_time": "10:00:00", "participant_count": 5,
    }, headers=auth_headers())
    assert request.status_code == 201, request.text
