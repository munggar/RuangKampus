from dataclasses import dataclass
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ruangkampus.config import get_settings
from ruangkampus.models import LectureSchedule, Reservation, Room, RoomUnavailablePeriod


@dataclass
class AvailabilityResult:
    available: bool
    reasons: list[str]


def _overlaps(start_a: time, end_a: time, start_b: time, end_b: time) -> bool:
    # Half-open intervals: adjacent bookings are allowed (09:00-10:00, 10:00-11:00).
    return start_a < end_b and start_b < end_a


def _within_operating_hours(room: Room, requested_date: date, start: time, end: time) -> bool:
    hours = room.operating_hours or {}
    weekday = requested_date.strftime("%A").lower()
    windows = hours.get(weekday, [])
    for window in windows:
        try:
            window_start = time.fromisoformat(window["start"] if isinstance(window["start"], str) else window["start"].isoformat())
            window_end = time.fromisoformat(window["end"] if isinstance(window["end"], str) else window["end"].isoformat())
        except (KeyError, TypeError, ValueError):
            continue
        if window_start <= start and end <= window_end:
            return True
    return False


def check_room_availability(
    db: Session,
    room: Room,
    requested_date: date,
    start_time: time,
    end_time: time,
    participant_count: int,
    exclude_reservation_id=None,
) -> AvailabilityResult:
    reasons: list[str] = []
    if not ensure_future_campus_time(requested_date, start_time):
        reasons.append("PAST_OR_CURRENT_START_TIME")
    if room.deleted_at is not None or room.room_status != "ACTIVE":
        reasons.append("ROOM_NOT_ACTIVE")
    if participant_count <= 0 or participant_count > room.capacity:
        reasons.append("CAPACITY_EXCEEDED")
    if not _within_operating_hours(room, requested_date, start_time, end_time):
        reasons.append("OUTSIDE_OPERATING_HOURS_OR_NOT_CONFIGURED")

    schedules = db.scalars(
        select(LectureSchedule).where(
            LectureSchedule.room_id == room.id,
            LectureSchedule.schedule_status == "ACTIVE",
            or_(LectureSchedule.schedule_date == requested_date,
                (LectureSchedule.schedule_date.is_(None) & (LectureSchedule.day_of_week == requested_date.weekday()))),
        )
    ).all()
    if any(_overlaps(start_time, end_time, item.start_time, item.end_time) for item in schedules):
        reasons.append("LECTURE_SCHEDULE_CONFLICT")

    blocks = db.scalars(select(RoomUnavailablePeriod).where(
        RoomUnavailablePeriod.room_id == room.id,
        RoomUnavailablePeriod.unavailable_date == requested_date,
        RoomUnavailablePeriod.is_active.is_(True),
    )).all()
    if any(_overlaps(start_time, end_time, item.start_time, item.end_time) for item in blocks):
        reasons.append("ROOM_UNAVAILABLE")

    reservation_stmt = select(Reservation).where(
        Reservation.room_id == room.id,
        Reservation.reservation_date == requested_date,
        Reservation.status.in_(["PENDING", "APPROVED"]),
    )
    if exclude_reservation_id is not None:
        reservation_stmt = reservation_stmt.where(Reservation.id != exclude_reservation_id)
    reservations = db.scalars(reservation_stmt).all()
    if any(_overlaps(start_time, end_time, item.start_time, item.end_time) for item in reservations):
        reasons.append("RESERVATION_CONFLICT")

    return AvailabilityResult(available=not reasons, reasons=reasons)


def ensure_future_campus_time(requested_date: date, start_time: time) -> bool:
    settings = get_settings()
    now_local = datetime.now(ZoneInfo(settings.campus_timezone))
    requested_local = datetime.combine(requested_date, start_time, tzinfo=ZoneInfo(settings.campus_timezone))
    return requested_local > now_local
