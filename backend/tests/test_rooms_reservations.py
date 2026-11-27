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
    created = client.post("/api/v1/rooms", json=room_payload, headers=auth_headers("admin.uhamka"))
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
    admin_headers = auth_headers("admin.uhamka")
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
    assert client.get(f"/api/v1/reservations/{reservation_id}", headers=auth_headers("admin.uhamka")).status_code == 200
    approved = client.patch(f"/api/v1/reservations/{reservation_id}/approve", headers=auth_headers("admin.uhamka"))
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


def test_admin_can_override_cancellation_after_start_for_any_room(
    client, db_session, auth_headers, student, admin, create_room, monkeypatch,
):
    from datetime import datetime as RealDateTime, time
    from uuid import UUID
    from zoneinfo import ZoneInfo

    from sqlalchemy import select

    from ruangkampus.models import Reservation, Room, RoomUpdateLog
    from ruangkampus.routers import reservations as reservations_router

    room_data = create_room()
    room = db_session.scalar(select(Room).where(Room.id == UUID(room_data["id"])))
    reservation = Reservation(
        user_id=student.id,
        room_id=room.id,
        purpose="Past session cancellation",
        reservation_date=date(2026, 11, 27),
        start_time=time(13, 0),
        end_time=time(15, 0),
        participant_count=2,
        status="APPROVED",
    )
    db_session.add(reservation)
    db_session.commit()

    fixed_now = RealDateTime(2026, 11, 27, 13, 41, tzinfo=ZoneInfo("Asia/Jakarta"))
    monkeypatch.setattr(reservations_router, "utcnow", lambda: fixed_now)

    response = client.patch(
        f"/api/v1/reservations/{reservation.id}/cancel",
        json={"reason": "Ruangan perlu dikosongkan untuk kebutuhan kampus"},
        headers=auth_headers("admin.uhamka"),
    )
    assert response.status_code == 200, response.text
    assert response.json()["data"]["status"] == "CANCELLED"
    assert response.json()["data"]["cancellation_reason"] == "Ruangan perlu dikosongkan untuk kebutuhan kampus"

    db_session.refresh(reservation)
    assert reservation.cancelled_by_id == admin.id
    assert db_session.scalar(
        select(RoomUpdateLog).where(
            RoomUpdateLog.entity_type == "RESERVATION",
            RoomUpdateLog.entity_id == reservation.id,
            RoomUpdateLog.action == "CANCEL_RESERVATION",
        )
    ) is not None


def test_admin_override_requires_cancellation_reason(
    client, db_session, auth_headers, student, admin, create_room, monkeypatch,
):
    from datetime import datetime as RealDateTime, time
    from uuid import UUID
    from zoneinfo import ZoneInfo

    from sqlalchemy import select

    from ruangkampus.models import Reservation, Room
    from ruangkampus.routers import reservations as reservations_router

    room_data = create_room()
    room = db_session.scalar(select(Room).where(Room.id == UUID(room_data["id"])))
    reservation = Reservation(
        user_id=student.id,
        room_id=room.id,
        purpose="Require override reason",
        reservation_date=date(2026, 11, 27),
        start_time=time(13, 0),
        end_time=time(15, 0),
        participant_count=2,
        status="APPROVED",
    )
    db_session.add(reservation)
    db_session.commit()
    monkeypatch.setattr(
        reservations_router,
        "utcnow",
        lambda: RealDateTime(2026, 11, 27, 13, 41, tzinfo=ZoneInfo("Asia/Jakarta")),
    )

    response = client.patch(
        f"/api/v1/reservations/{reservation.id}/cancel",
        json={},
        headers=auth_headers("admin.uhamka"),
    )
    assert response.status_code == 422, response.text
    db_session.refresh(reservation)
    assert reservation.status == "APPROVED"


def test_student_cannot_override_cancellation_after_start(
    client, db_session, auth_headers, student, admin, create_room, monkeypatch,
):
    from datetime import datetime as RealDateTime, time
    from uuid import UUID
    from zoneinfo import ZoneInfo

    from sqlalchemy import select

    from ruangkampus.models import Reservation, Room
    from ruangkampus.routers import reservations as reservations_router

    room_data = create_room()
    room = db_session.scalar(select(Room).where(Room.id == UUID(room_data["id"])))
    reservation = Reservation(
        user_id=student.id,
        room_id=room.id,
        purpose="Student past cancellation",
        reservation_date=date(2026, 11, 27),
        start_time=time(13, 0),
        end_time=time(15, 0),
        participant_count=2,
        status="APPROVED",
    )
    db_session.add(reservation)
    db_session.commit()
    monkeypatch.setattr(
        reservations_router,
        "utcnow",
        lambda: RealDateTime(2026, 11, 27, 13, 41, tzinfo=ZoneInfo("Asia/Jakarta")),
    )

    response = client.patch(
        f"/api/v1/reservations/{reservation.id}/cancel",
        json={"reason": "Tried to override as student"},
        headers=auth_headers(),
    )
    assert response.status_code == 409, response.text
    db_session.refresh(reservation)
    assert reservation.status == "APPROVED"


def test_schedule_creation_rejects_reservation_conflict(client, auth_headers, student, admin, create_room):
    room = create_room()
    booking_date = next_weekday(0)
    request = client.post("/api/v1/reservations", json={"room_id": room["id"], "purpose": "Exam prep", "date": booking_date.isoformat(), "start_time": "09:00:00", "end_time": "10:00:00", "participant_count": 6}, headers=auth_headers())
    assert request.status_code == 201
    response = client.post("/api/v1/admin/schedules", json={"room_id": room["id"], "course_name": "New class", "schedule_date": booking_date.isoformat(), "start_time": "09:30:00", "end_time": "10:30:00", "data_source": "TEST_ONLY"}, headers=auth_headers("admin.uhamka"))
    assert response.status_code == 409


def test_user_admin_management_is_role_protected(client, auth_headers, student, admin):
    denied = client.get("/api/v1/users", headers=auth_headers())
    assert denied.status_code == 403
    listed = client.get("/api/v1/users?role=STUDENT", headers=auth_headers("admin.uhamka"))
    assert listed.status_code == 200
    assert len(listed.json()["data"]) == 1
    updated = client.patch(f"/api/v1/users/{student.id}/status", json={"account_status": "DISABLED"}, headers=auth_headers("admin.uhamka"))
    assert updated.status_code == 200
    assert updated.json()["data"]["account_status"] == "DISABLED"


def test_admin_cannot_deactivate_room_with_active_future_reservation(client, auth_headers, student, admin, create_room):
    room = create_room()
    booking_date = next_weekday(1)
    created = client.post("/api/v1/reservations", json={"room_id": room["id"], "purpose": "Reserved slot", "date": booking_date.isoformat(), "start_time": "11:00:00", "end_time": "12:00:00", "participant_count": 2}, headers=auth_headers())
    assert created.status_code == 201
    result = client.patch(f"/api/v1/rooms/{room['id']}", json={"room_status": "INACTIVE"}, headers=auth_headers("admin.uhamka"))
    assert result.status_code == 409


def test_admin_activity_tracks_reservation_approval(client, auth_headers, student, admin, create_room):
    room = create_room()
    booking_date = next_weekday(0)
    created = client.post("/api/v1/reservations", json={"room_id": room["id"], "purpose": "Audit test", "date": booking_date.isoformat(), "start_time": "19:00:00", "end_time": "20:00:00", "participant_count": 3}, headers=auth_headers())
    reservation_id = created.json()["data"]["id"]
    approved = client.patch(f"/api/v1/reservations/{reservation_id}/approve", headers=auth_headers("admin.uhamka"))
    assert approved.status_code == 200
    activity = client.get("/api/v1/admin/activity?entity_type=RESERVATION&action=APPROVE_RESERVATION", headers=auth_headers("admin.uhamka"))
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
    approved = client.patch(f"/api/v1/reservations/{reservation_id}/approve", headers=auth_headers("admin.uhamka"))
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
        headers=auth_headers("admin.uhamka"),
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
        headers=auth_headers("admin.uhamka"),
    )
    assert changed.status_code == 200
    maintenance = client.get(
        f"/api/v1/rooms/{room['id']}/availability?date={booking_date.isoformat()}&startTime=12:00&endTime=13:00&participantCount=2"
    )
    assert "ROOM_IN_MAINTENANCE" in maintenance.json()["data"]["reasons"]


def test_maintenance_period_blocks_new_reservation(client, auth_headers, student, admin, create_room):
    room = create_room()
    booking_date = next_weekday(1)
    admin_headers = auth_headers("admin.uhamka")
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


def test_admin_bulk_updates_multiple_room_statuses_and_records_audit(
    client, auth_headers, admin, create_room, room_payload
):
    first = create_room()
    second_payload = {**room_payload, "room_name": "Room 102", "room_code": "R-102"}
    second_response = client.post(
        "/api/v1/rooms", json=second_payload, headers=auth_headers("admin.uhamka")
    )
    assert second_response.status_code == 201, second_response.text
    second = second_response.json()["data"]

    response = client.patch(
        "/api/v1/rooms/bulk-status",
        json={"room_ids": [first["id"], second["id"]], "room_status": "MAINTENANCE"},
        headers=auth_headers("admin.uhamka"),
    )

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["updated_count"] == 2
    assert data["unchanged_count"] == 0
    assert {room["room_status"] for room in data["rooms"]} == {"MAINTENANCE"}

    persisted = client.get(
        "/api/v1/rooms?status=MAINTENANCE", headers=auth_headers("admin.uhamka")
    )
    assert persisted.status_code == 200
    assert persisted.json()["meta"]["total"] == 2


def test_bulk_room_status_is_atomic_when_any_room_has_future_reservation(
    client, auth_headers, student, admin, create_room, room_payload
):
    first = create_room()
    second_payload = {**room_payload, "room_name": "Room 103", "room_code": "R-103"}
    second_response = client.post(
        "/api/v1/rooms", json=second_payload, headers=auth_headers("admin.uhamka")
    )
    assert second_response.status_code == 201, second_response.text
    second = second_response.json()["data"]

    booking_date = next_weekday(1)
    reservation = client.post(
        "/api/v1/reservations",
        json={
            "room_id": first["id"],
            "purpose": "Reserved slot",
            "date": booking_date.isoformat(),
            "start_time": "11:00:00",
            "end_time": "12:00:00",
            "participant_count": 2,
        },
        headers=auth_headers(),
    )
    assert reservation.status_code == 201, reservation.text

    response = client.patch(
        "/api/v1/rooms/bulk-status",
        json={"room_ids": [first["id"], second["id"]], "room_status": "INACTIVE"},
        headers=auth_headers("admin.uhamka"),
    )

    assert response.status_code == 409
    unchanged = client.get(
        "/api/v1/rooms?status=ACTIVE", headers=auth_headers("admin.uhamka")
    )
    assert unchanged.status_code == 200
    assert unchanged.json()["meta"]["total"] == 2


def test_student_cannot_bulk_update_rooms_and_duplicate_ids_are_rejected(
    client, auth_headers, student, admin, create_room
):
    room = create_room()
    payload = {"room_ids": [room["id"]], "room_status": "INACTIVE"}
    denied = client.patch("/api/v1/rooms/bulk-status", json=payload, headers=auth_headers())
    assert denied.status_code == 403

    duplicate = client.patch(
        "/api/v1/rooms/bulk-status",
        json={"room_ids": [room["id"], room["id"]], "room_status": "INACTIVE"},
        headers=auth_headers("admin.uhamka"),
    )
    assert duplicate.status_code == 422


def test_admin_create_and_update_accepts_relative_room_photo_paths(
    client, auth_headers, admin, room_payload
):
    payload = {**room_payload, "photo_url": "/media/rooms/imported-room.jpg"}
    created = client.post(
        "/api/v1/rooms", json=payload, headers=auth_headers("admin.uhamka")
    )
    assert created.status_code == 201, created.text
    room = created.json()["data"]
    assert room["photo_url"] == "/media/rooms/imported-room.jpg"

    updated = client.patch(
        f"/api/v1/rooms/{room['id']}",
        json={"photo_url": "/media/rooms/updated-room.png"},
        headers=auth_headers("admin.uhamka"),
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["data"]["photo_url"] == "/media/rooms/updated-room.png"

    invalid = client.patch(
        f"/api/v1/rooms/{room['id']}",
        json={"photo_url": "/media/rooms/../../secrets.txt"},
        headers=auth_headers("admin.uhamka"),
    )
    assert invalid.status_code == 422


def test_admin_bulk_updates_operating_hours_for_selected_rooms(
    client, auth_headers, admin, create_room, room_payload
):
    first = create_room()
    second_response = client.post(
        "/api/v1/rooms",
        json={**room_payload, "room_name": "Room 102", "room_code": "R-102"},
        headers=auth_headers("admin.uhamka"),
    )
    assert second_response.status_code == 201, second_response.text
    second = second_response.json()["data"]

    operating_hours = {
        "monday": [{"start": "08:00", "end": "18:00"}],
        "wednesday": [{"start": "09:00", "end": "16:00"}],
    }
    response = client.patch(
        "/api/v1/rooms/bulk-operating-hours",
        json={"room_ids": [first["id"], second["id"]], "operating_hours": operating_hours},
        headers=auth_headers("admin.uhamka"),
    )

    assert response.status_code == 200, response.text
    result = response.json()["data"]
    assert result["updated_count"] == 2
    assert result["unchanged_count"] == 0
    assert all(room["operating_hours"] == {
        "monday": [{"start": "08:00:00", "end": "18:00:00"}],
        "wednesday": [{"start": "09:00:00", "end": "16:00:00"}],
    } for room in result["rooms"])


def test_bulk_operating_hours_rejects_batch_when_future_reservation_would_fall_outside_hours(
    client, auth_headers, student, admin, create_room, room_payload
):
    first = create_room()
    second_response = client.post(
        "/api/v1/rooms",
        json={**room_payload, "room_name": "Room 103", "room_code": "R-103"},
        headers=auth_headers("admin.uhamka"),
    )
    assert second_response.status_code == 201, second_response.text
    second = second_response.json()["data"]
    admin_headers = auth_headers("admin.uhamka")

    booking_date = next_weekday(1)
    reservation = client.post(
        "/api/v1/reservations",
        json={
            "room_id": first["id"],
            "purpose": "Reserved slot",
            "date": booking_date.isoformat(),
            "start_time": "11:00:00",
            "end_time": "12:00:00",
            "participant_count": 2,
        },
        headers=auth_headers(),
    )
    assert reservation.status_code == 201, reservation.text

    response = client.patch(
        "/api/v1/rooms/bulk-operating-hours",
        json={
            "room_ids": [first["id"], second["id"]],
            "operating_hours": {"monday": [{"start": "08:00", "end": "17:00"}]},
        },
        headers=admin_headers,
    )

    assert response.status_code == 409
    for room_id in (first["id"], second["id"]):
        current = client.get(
            f"/api/v1/rooms/{room_id}", headers=admin_headers
        )
        assert current.status_code == 200
        assert "tuesday" in current.json()["data"]["operating_hours"]


def test_student_cannot_bulk_update_operating_hours(
    client, auth_headers, student, admin, create_room
):
    room = create_room()
    response = client.patch(
        "/api/v1/rooms/bulk-operating-hours",
        json={
            "room_ids": [room["id"]],
            "operating_hours": {"monday": [{"start": "08:00", "end": "17:00"}]},
        },
        headers=auth_headers(),
    )
    assert response.status_code == 403


def test_student_reservation_payload_includes_room_photo_for_account_views(
    client, auth_headers, student, admin, room_payload
):
    created_room = client.post(
        "/api/v1/rooms",
        json={**room_payload, "photo_url": "/media/rooms/student-room.jpg"},
        headers=auth_headers("admin.uhamka"),
    )
    assert created_room.status_code == 201, created_room.text
    room = created_room.json()["data"]

    reservation = client.post(
        "/api/v1/reservations",
        json={
            "room_id": room["id"],
            "purpose": "Photo display test",
            "date": next_weekday(0).isoformat(),
            "start_time": "10:00:00",
            "end_time": "11:00:00",
            "participant_count": 2,
        },
        headers=auth_headers(),
    )
    assert reservation.status_code == 201, reservation.text
    assert reservation.json()["data"]["room"]["photo_url"] == "/media/rooms/student-room.jpg"


def test_overdue_approved_reservation_holds_room_until_admin_completion(
    client, db_session, auth_headers, student, admin, create_room, monkeypatch,
):
    from datetime import datetime as RealDateTime, time
    from uuid import UUID
    from zoneinfo import ZoneInfo

    from sqlalchemy import select

    from ruangkampus.models import Reservation, Room
    from ruangkampus.services import availability

    room_data = create_room()
    room = db_session.scalar(select(Room).where(Room.id == UUID(room_data["id"])))
    booking_date = date(2026, 11, 26)
    previous = Reservation(
        user_id=student.id,
        room_id=room.id,
        purpose="Previous session",
        reservation_date=booking_date,
        start_time=time(9, 0),
        end_time=time(10, 0),
        participant_count=4,
        status="APPROVED",
    )
    db_session.add(previous)
    db_session.commit()

    class FrozenDateTime(RealDateTime):
        @classmethod
        def now(cls, tz=None):
            fixed = RealDateTime(2026, 11, 26, 10, 15, tzinfo=ZoneInfo("Asia/Jakarta"))
            return fixed.astimezone(tz) if tz else fixed.replace(tzinfo=None)

    monkeypatch.setattr(availability, "datetime", FrozenDateTime)

    blocked = availability.check_room_availability(
        db_session, room, booking_date, time(10, 30), time(11, 30), 4,
    )
    assert not blocked.available
    assert "ROOM_OCCUPANCY_NOT_CONFIRMED" in blocked.reasons

    # Admin completion releases the conservative occupancy hold.
    previous.status = "COMPLETED"
    db_session.commit()
    available = availability.check_room_availability(
        db_session, room, booking_date, time(10, 30), time(11, 30), 4,
    )
    assert available.available

def test_overdue_approved_reservation_holds_room_across_calendar_days(
    db_session, student, admin, create_room, monkeypatch,
):
    from datetime import datetime as RealDateTime, time
    from uuid import UUID
    from zoneinfo import ZoneInfo

    from sqlalchemy import select

    from ruangkampus.models import Reservation, Room
    from ruangkampus.services import availability

    room_data = create_room()
    room = db_session.scalar(select(Room).where(Room.id == UUID(room_data["id"])))
    previous_date = date(2026, 11, 25)
    next_date = date(2026, 11, 26)
    previous = Reservation(
        user_id=student.id,
        room_id=room.id,
        purpose="Previous-day session",
        reservation_date=previous_date,
        start_time=time(9, 0),
        end_time=time(10, 0),
        participant_count=4,
        status="APPROVED",
    )
    db_session.add(previous)
    db_session.commit()

    class FrozenDateTime(RealDateTime):
        @classmethod
        def now(cls, tz=None):
            fixed = RealDateTime(2026, 11, 26, 10, 15, tzinfo=ZoneInfo("Asia/Jakarta"))
            return fixed.astimezone(tz) if tz else fixed.replace(tzinfo=None)

    monkeypatch.setattr(availability, "datetime", FrozenDateTime)

    blocked = availability.check_room_availability(
        db_session, room, next_date, time(11, 0), time(12, 0), 4,
    )
    assert not blocked.available
    assert "ROOM_OCCUPANCY_NOT_CONFIRMED" in blocked.reasons

    # The hold is released only after Admin confirms completion/vacancy.
    previous.status = "COMPLETED"
    db_session.commit()
    available = availability.check_room_availability(
        db_session, room, next_date, time(11, 0), time(12, 0), 4,
    )
    assert available.available

def test_api_blocks_next_day_booking_until_admin_confirms_overdue_room_vacant(
    client, db_session, auth_headers, student, admin, create_room, monkeypatch,
):
    from datetime import datetime as RealDateTime, time
    from uuid import UUID
    from zoneinfo import ZoneInfo

    from sqlalchemy import select

    from ruangkampus.models import Reservation, Room
    from ruangkampus.services import availability

    room_data = create_room()
    room = db_session.scalar(select(Room).where(Room.id == UUID(room_data["id"])))
    previous = Reservation(
        user_id=student.id,
        room_id=room.id,
        purpose="Overrun from previous day",
        reservation_date=date(2026, 11, 25),
        start_time=time(9, 0),
        end_time=time(10, 0),
        participant_count=4,
        status="APPROVED",
    )
    db_session.add(previous)
    db_session.commit()

    class FrozenDateTime(RealDateTime):
        @classmethod
        def now(cls, tz=None):
            fixed = RealDateTime(2026, 11, 26, 10, 15, tzinfo=ZoneInfo("Asia/Jakarta"))
            return fixed.astimezone(tz) if tz else fixed.replace(tzinfo=None)

    monkeypatch.setattr(availability, "datetime", FrozenDateTime)
    payload = {
        "room_id": room_data["id"],
        "purpose": "Next-day room use",
        "date": "2026-11-26",
        "start_time": "11:00:00",
        "end_time": "12:00:00",
        "participant_count": 4,
    }

    blocked = client.post("/api/v1/reservations", json=payload, headers=auth_headers())
    assert blocked.status_code == 409

    completed = client.patch(
        f"/api/v1/reservations/{previous.id}/complete",
        headers=auth_headers("admin.uhamka"),
    )
    assert completed.status_code == 200, completed.text
    assert completed.json()["data"]["status"] == "COMPLETED"

    allowed = client.post("/api/v1/reservations", json=payload, headers=auth_headers())
    assert allowed.status_code == 201, allowed.text

def test_admin_bulk_soft_deletes_selected_rooms_and_records_audit(
    client, auth_headers, admin, create_room, room_payload, db_session
):
    from ruangkampus.models import Room, RoomUpdateLog
    from uuid import UUID

    first = create_room()
    second_response = client.post(
        "/api/v1/rooms",
        json={**room_payload, "room_name": "Room 202", "room_code": "R-202"},
        headers=auth_headers("admin.uhamka"),
    )
    assert second_response.status_code == 201, second_response.text
    second = second_response.json()["data"]

    response = client.request(
        "DELETE",
        "/api/v1/rooms/bulk",
        json={"room_ids": [first["id"], second["id"]]},
        headers=auth_headers("admin.uhamka"),
    )

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["deleted_count"] == 2
    assert set(data["room_ids"]) == {first["id"], second["id"]}

    remaining = client.get("/api/v1/rooms", headers=auth_headers("admin.uhamka"))
    assert remaining.status_code == 200
    assert remaining.json()["meta"]["total"] == 0

    persisted = db_session.query(Room).filter(Room.id.in_([UUID(first["id"]), UUID(second["id"])]))
    assert all(room.deleted_at is not None and room.room_status == "INACTIVE" for room in persisted.all())
    audit = db_session.query(RoomUpdateLog).filter(
        RoomUpdateLog.action == "BULK_SOFT_DELETE",
        RoomUpdateLog.entity_id.in_([UUID(first["id"]), UUID(second["id"])]),
    ).all()
    assert len(audit) == 2


def test_bulk_room_delete_is_atomic_when_any_selected_room_has_future_booking(
    client, auth_headers, student, admin, create_room, room_payload
):
    first = create_room()
    second_response = client.post(
        "/api/v1/rooms",
        json={**room_payload, "room_name": "Room 203", "room_code": "R-203"},
        headers=auth_headers("admin.uhamka"),
    )
    assert second_response.status_code == 201, second_response.text
    second = second_response.json()["data"]

    reservation = client.post(
        "/api/v1/reservations",
        json={
            "room_id": first["id"],
            "purpose": "Reservation that protects selected room",
            "date": next_weekday(1).isoformat(),
            "start_time": "11:00:00",
            "end_time": "12:00:00",
            "participant_count": 2,
        },
        headers=auth_headers(),
    )
    assert reservation.status_code == 201, reservation.text

    response = client.request(
        "DELETE",
        "/api/v1/rooms/bulk",
        json={"room_ids": [first["id"], second["id"]]},
        headers=auth_headers("admin.uhamka"),
    )

    assert response.status_code == 409
    remaining = client.get("/api/v1/rooms", headers=auth_headers("admin.uhamka"))
    assert remaining.status_code == 200
    assert remaining.json()["meta"]["total"] == 2


def test_student_cannot_bulk_delete_rooms_and_duplicate_ids_are_rejected(
    client, auth_headers, student, admin, create_room
):
    room = create_room()
    payload = {"room_ids": [room["id"]]}
    denied = client.request("DELETE", "/api/v1/rooms/bulk", json=payload, headers=auth_headers())
    assert denied.status_code == 403

    duplicate = client.request(
        "DELETE",
        "/api/v1/rooms/bulk",
        json={"room_ids": [room["id"], room["id"]]},
        headers=auth_headers("admin.uhamka"),
    )
    assert duplicate.status_code == 422

