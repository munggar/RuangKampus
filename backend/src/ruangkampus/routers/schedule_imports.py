from datetime import date, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ruangkampus.database import get_db
from ruangkampus.dependencies import require_admin
from ruangkampus.models import (
    LectureSchedule, Reservation, Room, RoomUnavailablePeriod,
    RoomUpdateLog, ScheduleImportBatch, User, utcnow,
)
from ruangkampus.responses import success
from ruangkampus.schemas import ScheduleImportCommitIn
from ruangkampus.services.availability import campus_today
from ruangkampus.services.schedule_import import (
    parse_date_value, parse_schedule_file, parse_time_value, parse_weekday,
)

router = APIRouter(prefix="/admin/schedules/imports", tags=["Schedule imports"])
PREVIEW_TTL = timedelta(hours=24)


def _overlap(start_a, end_a, start_b, end_b) -> bool:
    return start_a < end_b and start_b < end_a


def _same_occurrence(first: dict, second: dict) -> bool:
    if first.get("schedule_date") and second.get("schedule_date"):
        return first["schedule_date"] == second["schedule_date"]
    if first.get("day_of_week") is not None and second.get("day_of_week") is not None:
        return first["day_of_week"] == second["day_of_week"]
    dated, recurring = (first, second) if first.get("schedule_date") else (second, first)
    return bool(dated.get("schedule_date") and recurring.get("day_of_week") is not None
                and date.fromisoformat(dated["schedule_date"]).weekday() == recurring["day_of_week"])


def _normalise_row(raw: dict, db: Session, filename: str) -> dict:
    room_id_value = str(raw.get("room_id") or "").strip()
    room_code_value = str(raw.get("room_code") or "").strip()
    if room_id_value:
        try:
            room_uuid = UUID(room_id_value)
        except ValueError:
            raise ValueError("room_id must be a valid UUID") from None
        room = db.scalar(select(Room).where(Room.id == room_uuid, Room.deleted_at.is_(None)))
    elif room_code_value:
        room = db.scalar(select(Room).where(Room.room_code == room_code_value, Room.deleted_at.is_(None)))
    else:
        raise ValueError("room_code or room_id is required")
    if room is None:
        raise ValueError("Room was not found")
    if room.room_status != "ACTIVE":
        raise ValueError("Room is not active")

    course_name = str(raw.get("course_name") or "").strip()
    if not course_name or len(course_name) > 200:
        raise ValueError("course_name is required and must not exceed 200 characters")
    start_time = parse_time_value(raw.get("start_time"))
    end_time = parse_time_value(raw.get("end_time"))
    if end_time <= start_time:
        raise ValueError("end_time must be later than start_time")

    raw_date = raw.get("schedule_date")
    raw_day = raw.get("day_of_week")
    schedule_date = None
    day_of_week = None
    if raw_date not in (None, ""):
        if raw_day not in (None, ""):
            raise ValueError("Provide schedule_date or day_of_week, not both")
        schedule_date = parse_date_value(raw_date)
    elif raw_day not in (None, ""):
        day_of_week = parse_weekday(raw_day)
    else:
        raise ValueError("One of schedule_date or day_of_week is required")

    return {
        "row_number": raw.get("_row_number", 0),
        "room_id": str(room.id),
        "room_code": room.room_code,
        "course_name": course_name,
        "schedule_date": schedule_date.isoformat() if schedule_date else None,
        "day_of_week": day_of_week,
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "data_source": f"CSV_IMPORT:{filename}"[:240],
    }


def _existing_conflict(db: Session, row: dict, room_id: UUID) -> str | None:
    start = parse_time_value(row["start_time"])
    end = parse_time_value(row["end_time"])
    dated = date.fromisoformat(row["schedule_date"]) if row["schedule_date"] else None
    weekday = row["day_of_week"] if row["day_of_week"] is not None else dated.weekday()

    if dated is not None:
        schedules = db.scalars(select(LectureSchedule).where(
            LectureSchedule.room_id == room_id,
            LectureSchedule.schedule_status == "ACTIVE",
            or_(LectureSchedule.schedule_date == dated,
                (LectureSchedule.schedule_date.is_(None) & (LectureSchedule.day_of_week == weekday))),
        )).all()
        if any(_overlap(start, end, item.start_time, item.end_time) for item in schedules):
            return "LECTURE_SCHEDULE_CONFLICT"
        reservations = db.scalars(select(Reservation).where(
            Reservation.room_id == room_id,
            Reservation.reservation_date == dated,
            Reservation.status.in_(["PENDING", "APPROVED"]),
        )).all()
        if any(_overlap(start, end, item.start_time, item.end_time) for item in reservations):
            return "RESERVATION_CONFLICT"
        blocks = db.scalars(select(RoomUnavailablePeriod).where(
            RoomUnavailablePeriod.room_id == room_id,
            RoomUnavailablePeriod.unavailable_date == dated,
            RoomUnavailablePeriod.is_active.is_(True),
        )).all()
        if any(_overlap(start, end, item.start_time, item.end_time) for item in blocks):
            return "ROOM_UNAVAILABLE"
        return None

    recurring = db.scalars(select(LectureSchedule).where(
        LectureSchedule.room_id == room_id,
        LectureSchedule.schedule_status == "ACTIVE",
        LectureSchedule.day_of_week == weekday,
    )).all()
    if any(_overlap(start, end, item.start_time, item.end_time) for item in recurring):
        return "LECTURE_SCHEDULE_CONFLICT"

    today = campus_today()
    dated_schedules = db.scalars(select(LectureSchedule).where(
        LectureSchedule.room_id == room_id,
        LectureSchedule.schedule_status == "ACTIVE",
        LectureSchedule.schedule_date >= today,
    )).all()
    if any(item.schedule_date.weekday() == weekday and _overlap(start, end, item.start_time, item.end_time)
           for item in dated_schedules):
        return "LECTURE_SCHEDULE_CONFLICT"

    future_dates = db.scalars(select(RoomUnavailablePeriod.unavailable_date).where(
        RoomUnavailablePeriod.room_id == room_id,
        RoomUnavailablePeriod.unavailable_date >= today,
        RoomUnavailablePeriod.is_active.is_(True),
    ).distinct()).all()
    for target in future_dates:
        if target.weekday() != weekday:
            continue
        blocks = db.scalars(select(RoomUnavailablePeriod).where(
            RoomUnavailablePeriod.room_id == room_id,
            RoomUnavailablePeriod.unavailable_date == target,
            RoomUnavailablePeriod.is_active.is_(True),
        )).all()
        if any(_overlap(start, end, item.start_time, item.end_time) for item in blocks):
            return "ROOM_UNAVAILABLE"

    reservation_dates = db.scalars(select(Reservation.reservation_date).where(
        Reservation.room_id == room_id,
        Reservation.reservation_date >= today,
        Reservation.status.in_(["PENDING", "APPROVED"]),
    ).distinct()).all()
    for target in reservation_dates:
        if target.weekday() != weekday:
            continue
        reservations = db.scalars(select(Reservation).where(
            Reservation.room_id == room_id,
            Reservation.reservation_date == target,
            Reservation.status.in_(["PENDING", "APPROVED"]),
        )).all()
        if any(_overlap(start, end, item.start_time, item.end_time) for item in reservations):
            return "RESERVATION_CONFLICT"
    return None


def _batch_payload(batch: ScheduleImportBatch) -> dict:
    return {
        "batch_id": str(batch.id),
        "status": batch.status,
        "source_filename": batch.source_filename,
        "row_count": batch.row_count,
        "valid_count": batch.valid_count,
        "invalid_count": batch.invalid_count,
        "row_results": batch.row_results,
        "created_at": batch.created_at.isoformat(),
        "completed_at": batch.completed_at.isoformat() if batch.completed_at else None,
    }


@router.post("/preview", status_code=201)
async def preview_schedule_import(
    file: UploadFile = File(...),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    content = await file.read(5 * 1024 * 1024 + 1)
    filename, digest, source_rows = parse_schedule_file(file.filename, file.content_type, content)
    valid_rows = []
    results = []
    for raw in source_rows:
        try:
            row = _normalise_row(raw, db, filename)
            conflict = _existing_conflict(db, row, UUID(row["room_id"]))
            if conflict:
                raise ValueError(conflict)
            for earlier in valid_rows:
                if earlier["room_id"] == row["room_id"] and _same_occurrence(earlier, row) and _overlap(
                    parse_time_value(earlier["start_time"]), parse_time_value(earlier["end_time"]),
                    parse_time_value(row["start_time"]), parse_time_value(row["end_time"]),
                ):
                    raise ValueError(f"OVERLAPS_IMPORT_ROW_{earlier['row_number']}")
            valid_rows.append(row)
            results.append({"row_number": raw["_row_number"], "status": "VALID", "errors": [], "room_code": row["room_code"], "course_name": row["course_name"]})
        except ValueError as exc:
            results.append({"row_number": raw.get("_row_number", 0), "status": "INVALID", "errors": [str(exc)]})

    batch = ScheduleImportBatch(
        created_by_id=admin.id,
        status="PREVIEWED",
        source_filename=filename,
        file_sha256=digest,
        row_count=len(source_rows),
        valid_count=len(valid_rows),
        invalid_count=len(results) - len(valid_rows),
        parsed_rows=valid_rows,
        row_results=results,
    )
    db.add(batch)
    db.commit()
    db.refresh(batch)
    return success(_batch_payload(batch) | {"preview_rows": valid_rows[:50]}, "Schedule import preview created")


@router.post("/commit")
def commit_schedule_import(
    payload: ScheduleImportCommitIn,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    batch = db.scalar(select(ScheduleImportBatch).where(
        ScheduleImportBatch.id == payload.batch_id,
        ScheduleImportBatch.created_by_id == admin.id,
    ).with_for_update())
    if batch is None:
        raise HTTPException(status_code=404, detail="Schedule import batch not found")
    if batch.status != "PREVIEWED":
        raise HTTPException(status_code=409, detail="Only a previewed import batch can be committed")
    created_at = batch.created_at
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=utcnow().tzinfo)
    if created_at + PREVIEW_TTL <= utcnow():
        batch.status = "FAILED"
        db.commit()
        raise HTTPException(status_code=409, detail="Schedule import preview expired; upload the file again")
    rows = batch.parsed_rows
    if not rows:
        batch.status = "FAILED"
        db.commit()
        raise HTTPException(status_code=422, detail="The preview contains no valid schedule rows to import")

    room_ids = sorted({UUID(row["room_id"]) for row in rows}, key=str)
    rooms = db.scalars(select(Room).where(
        Room.id.in_(room_ids), Room.deleted_at.is_(None)
    ).order_by(Room.id).with_for_update()).all()
    room_by_id = {room.id: room for room in rooms}
    failures = []
    for row in rows:
        room_id = UUID(row["room_id"])
        room = room_by_id.get(room_id)
        reason = "ROOM_NOT_FOUND_OR_INACTIVE" if room is None or room.room_status != "ACTIVE" else _existing_conflict(db, row, room_id)
        if reason:
            failures.append({"row_number": row["row_number"], "status": "INVALID", "errors": [reason]})
    if failures:
        batch.status = "FAILED"
        batch.row_results = [
            next((failed for failed in failures if failed["row_number"] == item.get("row_number")), item)
            for item in batch.row_results
        ]
        batch.invalid_count += len(failures)
        db.commit()
        return JSONResponse(
            status_code=409,
            content={
                "success": False,
                "message": "Import was not committed because one or more schedules changed after preview",
                "errors": failures,
                "meta": {"batch_id": str(batch.id), "inserted": 0},
            },
        )

    for row in rows:
        schedule_date = date.fromisoformat(row["schedule_date"]) if row["schedule_date"] else None
        schedule = LectureSchedule(
            room_id=UUID(row["room_id"]),
            course_name=row["course_name"],
            schedule_date=schedule_date,
            day_of_week=row["day_of_week"],
            start_time=parse_time_value(row["start_time"]),
            end_time=parse_time_value(row["end_time"]),
            schedule_status="ACTIVE",
            data_source=row["data_source"],
        )
        db.add(schedule)
        db.flush()
        db.add(RoomUpdateLog(
            admin_id=admin.id,
            entity_type="LECTURE_SCHEDULE",
            entity_id=schedule.id,
            action="IMPORT_CREATE",
            previous_value=None,
            new_value={
                "room_id": str(schedule.room_id),
                "course_name": schedule.course_name,
                "schedule_date": schedule_date.isoformat() if schedule_date else None,
                "day_of_week": schedule.day_of_week,
                "start_time": schedule.start_time.isoformat(),
                "end_time": schedule.end_time.isoformat(),
                "data_source": schedule.data_source,
                "import_batch_id": str(batch.id),
            },
        ))
    batch.status = "COMPLETED"
    batch.completed_at = utcnow()
    db.commit()
    db.refresh(batch)
    return success(_batch_payload(batch) | {"inserted": len(rows)}, "Valid schedule rows imported atomically")


@router.get("")
def list_schedule_imports(
    limit: int = 20,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if limit < 1 or limit > 100:
        raise HTTPException(status_code=422, detail="limit must be between 1 and 100")
    items = db.scalars(select(ScheduleImportBatch).where(
        ScheduleImportBatch.created_by_id == admin.id,
    ).order_by(ScheduleImportBatch.created_at.desc()).limit(limit)).all()
    return success([_batch_payload(item) for item in items], "Schedule import history retrieved")


@router.get("/{batch_id}")
def get_schedule_import(
    batch_id: UUID,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    batch = db.scalar(select(ScheduleImportBatch).where(
        ScheduleImportBatch.id == batch_id,
        ScheduleImportBatch.created_by_id == admin.id,
    ))
    if batch is None:
        raise HTTPException(status_code=404, detail="Schedule import batch not found")
    return success(_batch_payload(batch) | {"preview_rows": batch.parsed_rows[:50]}, "Schedule import batch retrieved")
