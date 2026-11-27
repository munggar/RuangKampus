from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from sqlalchemy import func, select

from ruangkampus.models import Reservation

pytestmark = pytest.mark.postgres


def _payload(room_id, booking_date, start="09:00:00", end="11:00:00"):
    return {
        "room_id": str(room_id),
        "purpose": "PostgreSQL concurrent test",
        "date": booking_date.isoformat(),
        "start_time": start,
        "end_time": end,
        "participant_count": 10,
    }


def test_two_concurrent_overlapping_creates_do_not_double_book(
    pg_client, pg_session, pg_room, pg_users, pg_tokens, future_booking_date
):
    gate = Barrier(2)
    payload = _payload(pg_room.id, future_booking_date)

    def submit(user_key):
        gate.wait(timeout=10)
        return pg_client.post("/api/v1/reservations", json=payload, headers=pg_tokens[user_key])

    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(submit, "student_a")
        second = pool.submit(submit, "student_b")
        responses = [first.result(timeout=30), second.result(timeout=30)]

    assert sorted(response.status_code for response in responses) == [201, 409]
    count = pg_session.scalar(select(func.count(Reservation.id)).where(
        Reservation.room_id == pg_room.id,
        Reservation.reservation_date == future_booking_date,
        Reservation.status.in_(["PENDING", "APPROVED"]),
    ))
    assert count == 1


def test_concurrent_duplicate_approval_has_one_state_transition(
    pg_client, pg_session, pg_room, pg_users, pg_tokens, future_booking_date
):
    created = pg_client.post(
        "/api/v1/reservations",
        json=_payload(pg_room.id, future_booking_date),
        headers=pg_tokens["student_a"],
    )
    assert created.status_code == 201, created.text
    reservation_id = created.json()["data"]["id"]
    gate = Barrier(2)

    def approve():
        gate.wait(timeout=10)
        return pg_client.patch(
            f"/api/v1/reservations/{reservation_id}/approve",
            headers=pg_tokens["admin"],
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(approve)
        second = pool.submit(approve)
        responses = [first.result(timeout=30), second.result(timeout=30)]

    assert sorted(response.status_code for response in responses) == [200, 409]
    row = pg_session.get(Reservation, reservation_id)
    assert row.status == "APPROVED"


def test_concurrent_approval_and_overlapping_create_remain_serialized(
    pg_client, pg_session, pg_room, pg_users, pg_tokens, future_booking_date
):
    created = pg_client.post(
        "/api/v1/reservations",
        json=_payload(pg_room.id, future_booking_date),
        headers=pg_tokens["student_a"],
    )
    assert created.status_code == 201, created.text
    reservation_id = created.json()["data"]["id"]
    gate = Barrier(2)

    def approve_existing():
        gate.wait(timeout=10)
        return pg_client.patch(
            f"/api/v1/reservations/{reservation_id}/approve",
            headers=pg_tokens["admin"],
        )

    def create_overlap():
        gate.wait(timeout=10)
        return pg_client.post(
            "/api/v1/reservations",
            json=_payload(pg_room.id, future_booking_date, "10:00:00", "12:00:00"),
            headers=pg_tokens["student_b"],
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        approval_future = pool.submit(approve_existing)
        create_future = pool.submit(create_overlap)
        approval = approval_future.result(timeout=30)
        creation = create_future.result(timeout=30)

    assert approval.status_code == 200, approval.text
    assert creation.status_code == 409, creation.text
    active = pg_session.scalars(select(Reservation).where(
        Reservation.room_id == pg_room.id,
        Reservation.reservation_date == future_booking_date,
        Reservation.status.in_(["PENDING", "APPROVED"]),
    )).all()
    assert len(active) == 1
    assert active[0].status == "APPROVED"


def test_failed_reservation_transaction_leaves_no_partial_record(
    pg_client, pg_session, pg_room, pg_users, pg_tokens, future_booking_date
):
    payload = _payload(pg_room.id, future_booking_date)
    payload["participant_count"] = pg_room.capacity + 1
    response = pg_client.post("/api/v1/reservations", json=payload, headers=pg_tokens["student_a"])
    assert response.status_code == 409
    assert pg_session.scalar(select(func.count(Reservation.id))) == 0
