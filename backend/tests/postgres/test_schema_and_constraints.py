from datetime import time
import uuid

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError

from ruangkampus.models import LectureSchedule, Reservation

pytestmark = pytest.mark.postgres


def test_postgres_schema_has_required_tables_indexes_and_constraints(postgres_engine):
    inspector = inspect(postgres_engine)
    tables = set(inspector.get_table_names())
    expected = {
        "users", "auth_sessions", "password_reset_tokens", "rooms", "reservations",
        "lecture_schedules", "room_unavailability", "notifications", "room_update_logs",
        "schedule_import_batches", "alembic_version",
    }
    assert expected.issubset(tables)

    reservation_indexes = {item["name"] for item in inspector.get_indexes("reservations")}
    assert {"ix_reservations_room_date_status", "ix_reservations_user_date"}.issubset(reservation_indexes)
    notification_indexes = {item["name"] for item in inspector.get_indexes("notifications")}
    assert "uq_notifications_event_key" in notification_indexes

    reservation_fks = inspector.get_foreign_keys("reservations")
    assert any(item["referred_table"] == "rooms" for item in reservation_fks)
    assert any(item["referred_table"] == "users" for item in reservation_fks)
    room_checks = {item["name"] for item in inspector.get_check_constraints("rooms")}
    assert "ck_rooms_capacity_positive" in room_checks


def test_postgres_reports_version_and_transaction_isolation(postgres_engine):
    with postgres_engine.connect() as connection:
        version = connection.execute(text("SELECT current_setting('server_version_num')::int")).scalar_one()
        isolation = connection.execute(text("SHOW transaction_isolation")).scalar_one()
    assert version >= 140000
    assert isolation == "read committed"


def test_postgres_check_constraint_rejects_non_positive_participant_count(pg_session, pg_users, pg_room, future_booking_date):
    row = Reservation(
        user_id=pg_users["student_a"].id,
        room_id=pg_room.id,
        purpose="Constraint test",
        reservation_date=future_booking_date,
        start_time=time(9, 0),
        end_time=time(10, 0),
        participant_count=0,
        status="PENDING",
    )
    pg_session.add(row)
    with pytest.raises(IntegrityError):
        pg_session.commit()
    pg_session.rollback()
    assert pg_session.query(Reservation).count() == 0


def test_postgres_foreign_key_rejects_unknown_user(pg_session, pg_room, future_booking_date):
    row = Reservation(
        user_id=uuid.uuid4(),
        room_id=pg_room.id,
        purpose="Foreign key test",
        reservation_date=future_booking_date,
        start_time=time(9, 0),
        end_time=time(10, 0),
        participant_count=5,
        status="PENDING",
    )
    pg_session.add(row)
    with pytest.raises(IntegrityError):
        pg_session.commit()
    pg_session.rollback()
    assert pg_session.query(Reservation).count() == 0


def test_postgres_schedule_requires_exactly_one_date_or_weekday(pg_session, pg_room, future_booking_date):
    row = LectureSchedule(
        room_id=pg_room.id,
        course_name="Invalid discriminator",
        schedule_date=future_booking_date,
        day_of_week=future_booking_date.weekday(),
        start_time=time(9, 0),
        end_time=time(10, 0),
        schedule_status="ACTIVE",
        data_source="POSTGRES_TEST",
    )
    pg_session.add(row)
    with pytest.raises(IntegrityError):
        pg_session.commit()
    pg_session.rollback()
