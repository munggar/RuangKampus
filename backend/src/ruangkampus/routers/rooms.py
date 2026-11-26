from datetime import date, time
from math import ceil
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import String, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ruangkampus.database import get_db
from ruangkampus.dependencies import get_optional_user, require_admin
from ruangkampus.models import LectureSchedule, Reservation, Room, RoomUpdateLog, User, utcnow
from ruangkampus.responses import success
from ruangkampus.schemas import AvailabilityOut, RoomBulkStatusUpdateIn, RoomCreateIn, RoomUpdateIn, serialize_room
from ruangkampus.services.availability import campus_today, check_room_availability

router = APIRouter(prefix="/rooms", tags=["Rooms"])


def _room_or_404(db: Session, room_id: UUID, lock: bool = False) -> Room:
    stmt = select(Room).where(Room.id == room_id, Room.deleted_at.is_(None))
    if lock:
        stmt = stmt.with_for_update()
    room = db.scalar(stmt)
    if room is None:
        raise HTTPException(status_code=404, detail="Room not found")
    return room


def _room_snapshot(room: Room) -> dict:
    return {
        "room_name": room.room_name, "room_code": room.room_code, "building": room.building,
        "faculty": room.faculty, "floor": room.floor, "location_description": room.location_description,
        "capacity": room.capacity, "description": room.description,
        "facilities": room.facilities, "operating_hours": room.operating_hours,
        "room_status": room.room_status, "photo_url": room.photo_url,
    }


@router.get("")
def list_rooms(
    search: str | None = None,
    building: str | None = None,
    faculty: str | None = None,
    location: str | None = None,
    capacity: int | None = Query(default=None, ge=1),
    min_capacity: int | None = Query(default=None, ge=1),
    max_capacity: int | None = Query(default=None, ge=1),
    facilities: list[str] | None = Query(default=None),
    status: str | None = Query(default=None, pattern="^(ACTIVE|INACTIVE|MAINTENANCE)$"),
    available_date: date | None = Query(default=None, alias="date"),
    available_start: time | None = Query(default=None, alias="startTime"),
    available_end: time | None = Query(default=None, alias="endTime"),
    participant_count: int = Query(default=1, alias="participantCount", ge=1),
    sort_by: str = Query(default="room_name", alias="sortBy", pattern="^(room_name|building|faculty|floor|capacity|created_at)$"),
    sort_order: str = Query(default="asc", alias="sortOrder", pattern="^(asc|desc)$"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    stmt = select(Room).where(Room.deleted_at.is_(None))
    is_admin = current_user is not None and current_user.role == "TU_ADMIN"
    if is_admin:
        if status:
            stmt = stmt.where(Room.room_status == status)
    else:
        stmt = stmt.where(Room.room_status == "ACTIVE")
    if search:
        term = f"%{search.strip()}%"
        stmt = stmt.where(or_(
            Room.room_name.ilike(term), Room.room_code.ilike(term), Room.description.ilike(term),
            Room.building.ilike(term), Room.faculty.ilike(term), Room.location_description.ilike(term),
        ))
    if building:
        stmt = stmt.where(Room.building.ilike(f"%{building.strip()}%"))
    if faculty:
        stmt = stmt.where(Room.faculty.ilike(f"%{faculty.strip()}%"))
    if location:
        stmt = stmt.where(Room.location_description.ilike(f"%{location.strip()}%"))
    if (available_date is None) != (available_start is None) or (available_date is None) != (available_end is None):
        raise HTTPException(status_code=422, detail="date, startTime, and endTime must be supplied together")
    if available_start is not None and available_end is not None and available_end <= available_start:
        raise HTTPException(status_code=422, detail="endTime must be later than startTime")
    if capacity is not None:
        stmt = stmt.where(Room.capacity >= capacity)
    if min_capacity is not None:
        stmt = stmt.where(Room.capacity >= min_capacity)
    if max_capacity is not None:
        stmt = stmt.where(Room.capacity <= max_capacity)
    for facility in facilities or []:
        stmt = stmt.where(func.lower(Room.facilities.cast(String)).like(f"%{facility.lower()}%"))
    sort_column = getattr(Room, sort_by)
    stmt = stmt.order_by(sort_column.desc() if sort_order == "desc" else sort_column.asc())
    if available_date is not None and available_start is not None and available_end is not None:
        # Availability filtering happens before pagination so totals describe only reservable rooms.
        candidates = db.scalars(stmt).all()
        rooms = [
            room for room in candidates
            if check_room_availability(
                db, room, available_date, available_start, available_end, participant_count
            ).available
        ]
        total = len(rooms)
        page_rooms = rooms[(page - 1) * limit:page * limit]
    else:
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = db.scalar(count_stmt) or 0
        page_rooms = db.scalars(stmt.offset((page - 1) * limit).limit(limit)).all()
    items = [serialize_room(room) for room in page_rooms]
    meta = {"page": page, "limit": limit, "total": total, "total_pages": ceil(total / limit) if total else 0}
    return success(items, "Rooms retrieved", meta)


@router.patch("/bulk-status")
def bulk_update_room_status(
    payload: RoomBulkStatusUpdateIn,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Update selected room statuses atomically and retain one audit entry per changed room."""
    rooms = db.scalars(
        select(Room)
        .where(Room.id.in_(payload.room_ids), Room.deleted_at.is_(None))
        .order_by(Room.id)
        .with_for_update()
    ).all()
    if len(rooms) != len(payload.room_ids):
        raise HTTPException(status_code=404, detail="One or more selected rooms were not found")

    if payload.room_status in {"INACTIVE", "MAINTENANCE"}:
        blocked_rows = db.execute(
            select(Room.id, Room.room_name)
            .join(Reservation, Reservation.room_id == Room.id)
            .where(
                Room.id.in_(payload.room_ids),
                Reservation.status.in_(["PENDING", "APPROVED"]),
                Reservation.reservation_date >= campus_today(),
            )
            .distinct()
            .order_by(Room.room_name)
        ).all()
        if blocked_rows:
            names = ", ".join(row.room_name for row in blocked_rows)
            raise HTTPException(
                status_code=409,
                detail=(
                    "Status tidak dapat diubah karena ruangan berikut memiliki reservasi "
                    f"mendatang yang masih menunggu atau disetujui: {names}. "
                    "Tidak ada ruangan yang diubah."
                ),
            )

    now = utcnow()
    changed_rooms = []
    for room in rooms:
        if room.room_status == payload.room_status:
            continue
        previous = _room_snapshot(room)
        room.room_status = payload.room_status
        room.updated_at = now
        db.add(
            RoomUpdateLog(
                admin_id=admin.id,
                entity_type="ROOM",
                entity_id=room.id,
                action="BULK_STATUS_UPDATE",
                previous_value=previous,
                new_value=_room_snapshot(room),
            )
        )
        changed_rooms.append(room)

    db.commit()
    for room in rooms:
        db.refresh(room)

    return success(
        {
            "updated_count": len(changed_rooms),
            "unchanged_count": len(rooms) - len(changed_rooms),
            "rooms": [serialize_room(room) for room in rooms],
        },
        "Room statuses updated",
    )


@router.patch("/bulk-operating-hours")
def bulk_update_room_operating_hours(
    payload: RoomBulkOperatingHoursUpdateIn,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Apply one validated weekly schedule to selected rooms as an atomic operation."""
    rooms = db.scalars(
        select(Room)
        .where(Room.id.in_(payload.room_ids), Room.deleted_at.is_(None))
        .order_by(Room.id)
        .with_for_update()
    ).all()
    if len(rooms) != len(payload.room_ids):
        raise HTTPException(status_code=404, detail="One or more selected rooms were not found")

    proposed_hours = {
        day: [(window.start, window.end) for window in windows]
        for day, windows in payload.operating_hours.items()
    }
    room_names = {room.id: room.room_name for room in rooms}
    room_ids = list(room_names)
    today = campus_today()
    blocked: set[str] = set()

    future_reservations = db.scalars(
        select(Reservation).where(
            Reservation.room_id.in_(room_ids),
            Reservation.status.in_(["PENDING", "APPROVED"]),
            Reservation.reservation_date >= today,
        )
    ).all()
    weekday_keys = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    for reservation in future_reservations:
        day_key = weekday_keys[reservation.reservation_date.weekday()]
        windows = proposed_hours.get(day_key, [])
        if not any(start <= reservation.start_time and end >= reservation.end_time for start, end in windows):
            blocked.add(room_names[reservation.room_id])

    active_schedules = db.scalars(
        select(LectureSchedule).where(
            LectureSchedule.room_id.in_(room_ids),
            LectureSchedule.schedule_status == "ACTIVE",
        )
    ).all()
    for schedule in active_schedules:
        if schedule.schedule_date is not None:
            if schedule.schedule_date < today:
                continue
            weekday = schedule.schedule_date.weekday()
        elif schedule.day_of_week is not None:
            weekday = schedule.day_of_week
        else:
            continue
        day_key = weekday_keys[weekday]
        windows = proposed_hours.get(day_key, [])
        if not any(start <= schedule.start_time and end >= schedule.end_time for start, end in windows):
            blocked.add(room_names[schedule.room_id])

    if blocked:
        names = ", ".join(sorted(blocked))
        raise HTTPException(
            status_code=409,
            detail=(
                "Jam operasional tidak dapat diubah karena jadwal atau reservasi mendatang "
                f"pada ruangan berikut berada di luar jam yang dipilih: {names}. "
                "Tidak ada ruangan yang diubah."
            ),
        )

    normalized_hours = {
        day: [{"start": start.isoformat(), "end": end.isoformat()} for start, end in windows]
        for day, windows in proposed_hours.items()
    }
    now = utcnow()
    changed_rooms = []
    for room in rooms:
        previous = _room_snapshot(room)
        if room.operating_hours == normalized_hours:
            continue
        room.operating_hours = normalized_hours
        room.updated_at = now
        db.add(
            RoomUpdateLog(
                admin_id=admin.id,
                entity_type="ROOM",
                entity_id=room.id,
                action="BULK_OPERATING_HOURS_UPDATE",
                previous_value=previous,
                new_value=_room_snapshot(room),
            )
        )
        changed_rooms.append(room)

    db.commit()
    for room in rooms:
        db.refresh(room)

    return success(
        {
            "updated_count": len(changed_rooms),
            "unchanged_count": len(rooms) - len(changed_rooms),
            "rooms": [serialize_room(room) for room in rooms],
        },
        "Room operating hours updated",
    )


@router.get("/{room_id}")
def get_room(room_id: UUID, current_user: User | None = Depends(get_optional_user), db: Session = Depends(get_db)):
    room = _room_or_404(db, room_id)
    is_admin = current_user is not None and current_user.role == "TU_ADMIN"
    if room.room_status != "ACTIVE" and not is_admin:
        raise HTTPException(status_code=404, detail="Room not found")
    return success(serialize_room(room), "Room retrieved")


@router.get("/{room_id}/availability")
def get_availability(
    room_id: UUID,
    date_value: date = Query(alias="date"),
    start_time: time = Query(alias="startTime"),
    end_time: time = Query(alias="endTime"),
    participant_count: int = Query(default=1, alias="participantCount", ge=1),
    db: Session = Depends(get_db),
):
    if end_time <= start_time:
        raise HTTPException(status_code=422, detail="endTime must be later than startTime")
    room = _room_or_404(db, room_id)
    result = check_room_availability(db, room, date_value, start_time, end_time, participant_count)
    payload = AvailabilityOut(room_id=room.id, available=result.available, reasons=result.reasons, checked_at=utcnow()).model_dump(mode="json")
    return success(payload, "Availability checked")


@router.post("", status_code=201)
def create_room(payload: RoomCreateIn, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    data = payload.model_dump(mode="json")
    room = Room(**data)
    db.add(room)
    try:
        db.flush()
        db.add(RoomUpdateLog(admin_id=admin.id, entity_type="ROOM", entity_id=room.id, action="CREATE", previous_value=None, new_value=_room_snapshot(room)))
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Room code already exists") from None
    db.refresh(room)
    return success(serialize_room(room), "Room created")


@router.patch("/{room_id}")
def update_room(room_id: UUID, payload: RoomUpdateIn, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    room = _room_or_404(db, room_id, lock=True)
    previous = _room_snapshot(room)
    changes = payload.model_dump(exclude_unset=True, mode="json")
    if "capacity" in changes and changes["capacity"] < room.capacity:
        future_bookings = db.scalars(select(Reservation).where(
            Reservation.room_id == room.id,
            Reservation.status.in_(["PENDING", "APPROVED"]),
            Reservation.reservation_date >= campus_today(),
            Reservation.participant_count > changes["capacity"],
        )).all()
        if future_bookings:
            raise HTTPException(status_code=409, detail="Capacity cannot be reduced below an active reservation's participant count")
    if changes.get("room_status") in {"INACTIVE", "MAINTENANCE"}:
        active_bookings = db.scalar(select(func.count(Reservation.id)).where(
            Reservation.room_id == room.id,
            Reservation.status.in_(["PENDING", "APPROVED"]),
            Reservation.reservation_date >= campus_today(),
        )) or 0
        if active_bookings:
            raise HTTPException(status_code=409, detail="Room status cannot be changed while future pending/approved reservations exist")
    for key, value in changes.items():
        setattr(room, key, value)
    room.updated_at = utcnow()
    try:
        db.flush()
        db.add(RoomUpdateLog(admin_id=admin.id, entity_type="ROOM", entity_id=room.id, action="UPDATE", previous_value=previous, new_value=_room_snapshot(room)))
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Room code already exists") from None
    db.refresh(room)
    return success(serialize_room(room), "Room updated")


@router.delete("/{room_id}")
def soft_delete_room(room_id: UUID, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    room = _room_or_404(db, room_id, lock=True)
    previous = _room_snapshot(room)
    active_bookings = db.scalar(select(func.count(Reservation.id)).where(
        Reservation.room_id == room.id,
        Reservation.status.in_(["PENDING", "APPROVED"]),
        Reservation.reservation_date >= campus_today(),
    )) or 0
    if active_bookings:
        raise HTTPException(status_code=409, detail="Room cannot be deleted while future pending/approved reservations exist")
    now = utcnow()
    room.deleted_at = now
    room.room_status = "INACTIVE"
    room.updated_at = now
    db.add(RoomUpdateLog(admin_id=admin.id, entity_type="ROOM", entity_id=room.id, action="SOFT_DELETE", previous_value=previous, new_value=_room_snapshot(room)))
    db.commit()
    return success({"id": str(room.id), "deleted": True}, "Room deactivated and retained for reservation history")
