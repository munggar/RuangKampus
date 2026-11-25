from datetime import date, datetime
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ruangkampus.config import get_settings
from ruangkampus.database import get_db
from ruangkampus.dependencies import require_admin
from ruangkampus.models import LectureSchedule, Reservation, Room, RoomUnavailablePeriod, RoomUpdateLog, User, utcnow
from ruangkampus.responses import success
from ruangkampus.schemas import ScheduleCreateIn, ScheduleOut, UnavailabilityCreateIn
from ruangkampus.services.availability import check_room_availability

router = APIRouter(prefix="/admin", tags=["Schedules and maintenance"])


def _overlap(start_a, end_a, start_b, end_b) -> bool:
    return start_a < end_b and start_b < end_a


@router.get("/schedules")
def list_schedules(room_id: UUID | None = None, schedule_date: date | None = Query(default=None, alias="date"), db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    stmt = select(LectureSchedule)
    if room_id:
        stmt = stmt.where(LectureSchedule.room_id == room_id)
    if schedule_date:
        stmt = stmt.where((LectureSchedule.schedule_date == schedule_date) | (LectureSchedule.day_of_week == schedule_date.weekday()))
    schedules = db.scalars(stmt.order_by(LectureSchedule.last_updated_at.desc())).all()
    return success([ScheduleOut.model_validate(item).model_dump(mode="json") for item in schedules], "Schedules retrieved")


@router.post("/schedules", status_code=201)
def create_schedule(payload: ScheduleCreateIn, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    room = db.scalar(select(Room).where(Room.id == payload.room_id, Room.deleted_at.is_(None)).with_for_update())
    if room is None:
        raise HTTPException(status_code=404, detail="Room not found")
    campus_today = datetime.now(ZoneInfo(get_settings().campus_timezone)).date()
    target_dates: list[date] = []
    if payload.schedule_date is not None:
        target_dates = [payload.schedule_date]
    else:
        recurring_schedules = db.scalars(select(LectureSchedule).where(
            LectureSchedule.room_id == room.id, LectureSchedule.schedule_status == "ACTIVE",
            LectureSchedule.schedule_date.is_(None), LectureSchedule.day_of_week == payload.day_of_week,
        )).all()
        dated_schedules = db.scalars(select(LectureSchedule).where(
            LectureSchedule.room_id == room.id, LectureSchedule.schedule_status == "ACTIVE",
            LectureSchedule.schedule_date >= campus_today,
        )).all()
        if any(item.schedule_date.weekday() == payload.day_of_week and _overlap(payload.start_time, payload.end_time, item.start_time, item.end_time) for item in dated_schedules) or any(_overlap(payload.start_time, payload.end_time, item.start_time, item.end_time) for item in recurring_schedules):
            raise HTTPException(status_code=409, detail="Recurring schedule overlaps an existing lecture schedule")
        future_reservation_dates = db.scalars(select(Reservation.reservation_date).where(
            Reservation.room_id == room.id, Reservation.reservation_date >= campus_today,
            Reservation.status.in_(["PENDING", "APPROVED"]),
        ).distinct()).all()
        target_dates = [day for day in future_reservation_dates if day.weekday() == payload.day_of_week]

    for target_date in target_dates:
        existing_schedules = db.scalars(select(LectureSchedule).where(
            LectureSchedule.room_id == room.id, LectureSchedule.schedule_status == "ACTIVE",
            or_(LectureSchedule.schedule_date == target_date, (LectureSchedule.schedule_date.is_(None) & (LectureSchedule.day_of_week == target_date.weekday()))),
        )).all()
        if any(_overlap(payload.start_time, payload.end_time, item.start_time, item.end_time) for item in existing_schedules):
            raise HTTPException(status_code=409, detail="Schedule conflicts with another active lecture schedule")
        active_reservations = db.scalars(select(Reservation).where(
            Reservation.room_id == room.id, Reservation.reservation_date == target_date,
            Reservation.status.in_(["PENDING", "APPROVED"]),
        )).all()
        if any(_overlap(payload.start_time, payload.end_time, item.start_time, item.end_time) for item in active_reservations):
            raise HTTPException(status_code=409, detail="Schedule conflicts with an active reservation")
        active_blocks = db.scalars(select(RoomUnavailablePeriod).where(
            RoomUnavailablePeriod.room_id == room.id, RoomUnavailablePeriod.unavailable_date == target_date,
            RoomUnavailablePeriod.is_active.is_(True),
        )).all()
        if any(_overlap(payload.start_time, payload.end_time, item.start_time, item.end_time) for item in active_blocks):
            raise HTTPException(status_code=409, detail="Schedule conflicts with a maintenance/unavailability block")

    schedule = LectureSchedule(**payload.model_dump())
    db.add(schedule)
    db.flush()
    db.add(RoomUpdateLog(
        admin_id=admin.id, entity_type="LECTURE_SCHEDULE", entity_id=schedule.id, action="CREATE",
        previous_value=None,
        new_value={"room_id": str(schedule.room_id), "course_name": schedule.course_name,
            "schedule_date": schedule.schedule_date.isoformat() if schedule.schedule_date else None,
            "day_of_week": schedule.day_of_week, "start_time": schedule.start_time.isoformat(),
            "end_time": schedule.end_time.isoformat(), "schedule_status": schedule.schedule_status,
            "data_source": schedule.data_source},
    ))
    db.commit()
    db.refresh(schedule)
    return success(ScheduleOut.model_validate(schedule).model_dump(mode="json"), "Lecture schedule created")


@router.delete("/schedules/{schedule_id}")
def cancel_schedule(schedule_id: UUID, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    schedule = db.scalar(select(LectureSchedule).where(LectureSchedule.id == schedule_id).with_for_update())
    if schedule is None:
        raise HTTPException(status_code=404, detail="Schedule not found")
    previous = {"schedule_status": schedule.schedule_status}
    schedule.schedule_status = "CANCELLED"
    schedule.last_updated_at = utcnow()
    db.add(RoomUpdateLog(admin_id=admin.id, entity_type="LECTURE_SCHEDULE", entity_id=schedule.id, action="CANCEL", previous_value=previous, new_value={"schedule_status": "CANCELLED"}))
    db.commit()
    return success({"id": str(schedule.id), "schedule_status": schedule.schedule_status}, "Schedule cancelled")


@router.get("/room-unavailability")
def list_unavailability(room_id: UUID | None = None, unavailable_date: date | None = Query(default=None, alias="date"), admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    stmt = select(RoomUnavailablePeriod).where(RoomUnavailablePeriod.is_active.is_(True))
    if room_id:
        stmt = stmt.where(RoomUnavailablePeriod.room_id == room_id)
    if unavailable_date:
        stmt = stmt.where(RoomUnavailablePeriod.unavailable_date == unavailable_date)
    rows = db.scalars(stmt.order_by(RoomUnavailablePeriod.unavailable_date, RoomUnavailablePeriod.start_time)).all()
    data = [{"id": str(row.id), "room_id": str(row.room_id), "unavailable_date": row.unavailable_date.isoformat(), "start_time": row.start_time.isoformat(), "end_time": row.end_time.isoformat(), "reason": row.reason, "is_active": row.is_active} for row in rows]
    return success(data, "Room unavailability retrieved")


@router.post("/room-unavailability", status_code=201)
def create_unavailability(payload: UnavailabilityCreateIn, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    room = db.scalar(select(Room).where(Room.id == payload.room_id, Room.deleted_at.is_(None)).with_for_update())
    if room is None:
        raise HTTPException(status_code=404, detail="Room not found")
    result = check_room_availability(db, room, payload.unavailable_date, payload.start_time, payload.end_time, 1)
    blocking = [reason for reason in result.reasons if reason in {"RESERVATION_CONFLICT", "LECTURE_SCHEDULE_CONFLICT", "ROOM_UNAVAILABLE"}]
    if blocking:
        raise HTTPException(status_code=409, detail="Maintenance period conflicts with an existing schedule, reservation, or block")
    block = RoomUnavailablePeriod(**payload.model_dump(), created_by_id=admin.id)
    db.add(block)
    db.flush()
    db.add(RoomUpdateLog(admin_id=admin.id, entity_type="ROOM_UNAVAILABILITY", entity_id=block.id, action="CREATE", previous_value=None,
        new_value={"room_id": str(block.room_id), "unavailable_date": block.unavailable_date.isoformat(), "start_time": block.start_time.isoformat(), "end_time": block.end_time.isoformat(), "reason": block.reason}))
    db.commit()
    db.refresh(block)
    return success({"id": str(block.id), "room_id": str(block.room_id), "unavailable_date": block.unavailable_date.isoformat(), "start_time": block.start_time.isoformat(), "end_time": block.end_time.isoformat(), "reason": block.reason, "is_active": block.is_active}, "Room unavailability created")


@router.patch("/room-unavailability/{block_id}/deactivate")
def deactivate_unavailability(block_id: UUID, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    block = db.scalar(select(RoomUnavailablePeriod).where(RoomUnavailablePeriod.id == block_id).with_for_update())
    if block is None:
        raise HTTPException(status_code=404, detail="Unavailability record not found")
    block.is_active = False
    db.add(RoomUpdateLog(admin_id=admin.id, entity_type="ROOM_UNAVAILABILITY", entity_id=block.id, action="DEACTIVATE", previous_value={"is_active": True}, new_value={"is_active": False}))
    db.commit()
    return success({"id": str(block.id), "is_active": False}, "Room unavailability deactivated")


@router.get("/activity")
def list_admin_activity(entity_type: str | None = None, action: str | None = None, page: int = Query(default=1, ge=1), limit: int = Query(default=20, ge=1, le=100), admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    from math import ceil
    from sqlalchemy import func
    stmt = select(RoomUpdateLog, User).join(User, User.id == RoomUpdateLog.admin_id)
    if entity_type:
        stmt = stmt.where(RoomUpdateLog.entity_type == entity_type.upper())
    if action:
        stmt = stmt.where(RoomUpdateLog.action == action.upper())
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.execute(stmt.order_by(RoomUpdateLog.created_at.desc()).offset((page - 1) * limit).limit(limit)).all()
    data = [{"id": str(log.id), "admin": {"id": str(actor.id), "name": actor.name, "email": actor.email},
        "entity_type": log.entity_type, "entity_id": str(log.entity_id), "action": log.action,
        "previous_value": log.previous_value, "new_value": log.new_value, "created_at": log.created_at.isoformat()} for log, actor in rows]
    meta = {"page": page, "limit": limit, "total": total, "total_pages": ceil(total / limit) if total else 0}
    return success(data, "Administrator activity retrieved", meta)
