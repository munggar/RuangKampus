import re
from datetime import date, datetime, time, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy import String, func, or_, select
from sqlalchemy.orm import Session

from ruangkampus.database import get_db
from ruangkampus.dependencies import require_student
from ruangkampus.models import Room, User
from ruangkampus.responses import success
from ruangkampus.schemas import (
    AlternativeSlotsIn,
    AssistantChatIn,
    AssistantChatResponseData,
    AssistantChatSlots,
    AssistantChatStructuredData,
    serialize_room,
)
from ruangkampus.services.assistant_catalog import FACILITY_TERMS
from ruangkampus.services.availability import check_room_availability, campus_today


router = APIRouter(tags=["Room discovery and assistant"])

WEEKDAYS = {
    "senin": 0, "monday": 0,
    "selasa": 1, "tuesday": 1,
    "rabu": 2, "wednesday": 2,
    "kamis": 3, "thursday": 3,
    "jumat": 4, "friday": 4,
    "sabtu": 5, "saturday": 5,
    "minggu": 6, "sunday": 6,
}
STOP_WORDS = {
    "saya", "mau", "ingin", "tolong", "carikan", "cari", "ruangan", "ruang",
    "untuk", "orang", "peserta", "kapasitas", "di", "pada", "hari", "tanggal",
    "dengan", "yang", "ada", "buat", "booking", "reservasi", "peminjaman",
    "gedung", "fakultas", "dan", "atau", "butuh", "bisa", "apakah",
}
def _parse_time(value: str | time) -> time:
    return value if isinstance(value, time) else time.fromisoformat(value)


def _room_candidates(
    db: Session,
    *,
    faculty: str | None = None,
    building: str | None = None,
    min_capacity: int | None = None,
    facilities: list[str] | None = None,
    search_terms: list[str] | None = None,
):
    stmt = select(Room).where(
        Room.deleted_at.is_(None),
        Room.room_status == "ACTIVE",
    )
    if faculty:
        stmt = stmt.where(Room.faculty.ilike(f"%{faculty.strip()}%"))
    if building:
        stmt = stmt.where(Room.building.ilike(f"%{building.strip()}%"))
    if min_capacity:
        stmt = stmt.where(Room.capacity >= min_capacity)
    for facility in facilities or []:
        stmt = stmt.where(func.lower(Room.facilities.cast(String)).like(f"%{facility.lower()}%"))
    for term in search_terms or []:
        pattern = f"%{term}%"
        stmt = stmt.where(or_(
            Room.room_name.ilike(pattern),
            Room.room_code.ilike(pattern),
            Room.faculty.ilike(pattern),
            Room.building.ilike(pattern),
            Room.floor.ilike(pattern),
            Room.location_description.ilike(pattern),
            Room.description.ilike(pattern),
        ))
    return db.scalars(stmt.order_by(Room.room_name.asc()).limit(250)).all()


def find_alternative_slots(db: Session, request: AlternativeSlotsIn) -> list[dict]:
    rooms = _room_candidates(
        db,
        faculty=request.faculty,
        building=request.building,
        min_capacity=request.participant_count,
        facilities=request.facilities,
    )
    ranked: list[tuple[tuple[int, int, int, int], dict]] = []
    preferred_minutes = (
        request.preferred_start_time.hour * 60 + request.preferred_start_time.minute
        if request.preferred_start_time else 9 * 60
    )
    for day_offset in range(request.search_days + 1):
        candidate_date = request.date + timedelta(days=day_offset)
        weekday = candidate_date.strftime("%A").lower()
        for room in rooms:
            for window in (room.operating_hours or {}).get(weekday, []):
                try:
                    window_start = _parse_time(window["start"])
                    window_end = _parse_time(window["end"])
                except (KeyError, TypeError, ValueError):
                    continue
                current = datetime.combine(candidate_date, window_start)
                window_finish = datetime.combine(candidate_date, window_end)
                while current + timedelta(minutes=request.duration_minutes) <= window_finish:
                    start_time = current.time()
                    end_time = (current + timedelta(minutes=request.duration_minutes)).time()
                    availability = check_room_availability(
                        db, room, candidate_date, start_time, end_time, request.participant_count
                    )
                    if availability.available:
                        minute_of_day = start_time.hour * 60 + start_time.minute
                        time_distance = abs(minute_of_day - preferred_minutes)
                        same_room_penalty = 0 if request.room_id and room.id == request.room_id else 1
                        capacity_slack = room.capacity - request.participant_count
                        reason = []
                        if same_room_penalty == 0:
                            reason.append("SAME_ROOM")
                        if day_offset == 0:
                            reason.append("SAME_DATE")
                        if time_distance == 0:
                            reason.append("PREFERRED_TIME")
                        ranked.append((
                            (day_offset, time_distance, same_room_penalty, capacity_slack),
                            {
                                "room": serialize_room(room),
                                "date": candidate_date.isoformat(),
                                "start_time": start_time.isoformat(),
                                "end_time": end_time.isoformat(),
                                "participant_count": request.participant_count,
                                "duration_minutes": request.duration_minutes,
                                "match_reasons": reason,
                                "availability_source": "LIVE_AVAILABILITY_CHECK",
                            },
                        ))
                    current += timedelta(minutes=request.slot_step_minutes)
    ranked.sort(key=lambda item: item[0])
    return [item for _, item in ranked[:request.limit]]


def _parse_message_filters(db: Session, payload: AssistantChatIn) -> dict:
    message = payload.message.lower()
    min_capacity = payload.min_capacity
    if min_capacity is None:
        capacity_match = re.search(r"\b(\d{1,4})\s*(?:orang|peserta|pax|people|person)\b", message)
        if capacity_match:
            min_capacity = int(capacity_match.group(1))

    building = payload.building
    if building is None:
        building_match = re.search(r"\b(?:gedung|building)\s+([a-z0-9][a-z0-9._-]*)", message)
        if building_match:
            building = building_match.group(1)

    faculty = payload.faculty
    if faculty is None:
        faculty_names = db.scalars(
            select(Room.faculty).where(Room.faculty.is_not(None)).distinct()
        ).all()
        faculty = next((name for name in faculty_names if name and name.lower() in message), None)

    facilities = list(payload.facilities)
    if not facilities:
        for canonical, aliases in FACILITY_TERMS.items():
            if any(alias in message for alias in aliases):
                facilities.append(canonical)

    requested_date = payload.requested_date
    if requested_date is None:
        date_match = re.search(r"\b(20\d{2}-\d{2}-\d{2})\b", message)
        if date_match:
            try:
                requested_date = date.fromisoformat(date_match.group(1))
            except ValueError:
                requested_date = None
        elif "besok" in message:
            requested_date = campus_today() + timedelta(days=1)
        else:
            for label, weekday in WEEKDAYS.items():
                if re.search(rf"\b{label}\b", message):
                    today = campus_today()
                    delta = (weekday - today.weekday()) % 7
                    requested_date = today + timedelta(days=delta or 7)
                    break

    start_time, end_time = payload.start_time, payload.end_time
    if start_time is None and end_time is None:
        time_match = re.search(
            r"\b([01]?\d|2[0-3])[:.]([0-5]\d)\s*(?:-|sampai|hingga|to)\s*([01]?\d|2[0-3])[:.]([0-5]\d)\b",
            message,
        )
        if time_match:
            start_time = time(int(time_match.group(1)), int(time_match.group(2)))
            end_time = time(int(time_match.group(3)), int(time_match.group(4)))

    tokens = [
        token for token in re.findall(r"[a-z0-9-]+", message)
        if len(token) >= 3 and token not in STOP_WORDS and not token.isdigit()
    ]
    # Facility and room metadata terms are handled by their own structured filters.
    for aliases in FACILITY_TERMS.values():
        tokens = [token for token in tokens if token not in aliases]
    if building:
        tokens = [token for token in tokens if token != building.lower()]
    return {
        "faculty": faculty,
        "building": building,
        "min_capacity": min_capacity,
        "facilities": facilities,
        "date": requested_date,
        "start_time": start_time,
        "end_time": end_time,
        "participant_count": payload.participant_count,
        "search_terms": list(dict.fromkeys(tokens))[:5],
    }


@router.post("/rooms/alternative-slots")
def alternative_slots(
    payload: AlternativeSlotsIn,
    user: User = Depends(require_student),
    db: Session = Depends(get_db),
):
    items = find_alternative_slots(db, payload)
    data = {
        "items": items,
        "criteria": {
            "requested_date": payload.date.isoformat(),
            "duration_minutes": payload.duration_minutes,
            "participant_count": payload.participant_count,
            "search_days": payload.search_days,
            "slot_step_minutes": payload.slot_step_minutes,
        },
        "availability_note": "Alternatif dihitung dari data jadwal saat ini; reservasi tetap divalidasi ulang ketika dikirim.",
    }
    return success(data, "Alternative room slots retrieved")


@router.post("/assistant/chat")
def room_assistant_chat(
    payload: AssistantChatIn,
    user: User = Depends(require_student),
    db: Session = Depends(get_db),
):
    filters = _parse_message_filters(db, payload)
    rooms = _room_candidates(
        db,
        faculty=filters["faculty"],
        building=filters["building"],
        min_capacity=filters["min_capacity"],
        facilities=filters["facilities"],
        search_terms=filters["search_terms"],
    )

    available = []
    if filters["date"] and filters["start_time"] and filters["end_time"]:
        available = [
            room for room in rooms
            if check_room_availability(
                db, room, filters["date"], filters["start_time"], filters["end_time"],
                filters["participant_count"],
            ).available
        ]
        rooms = available

    alternatives = []
    if not rooms and filters["date"] and filters["start_time"] and filters["end_time"]:
        duration = int(
            (
                datetime.combine(filters["date"], filters["end_time"])
                - datetime.combine(filters["date"], filters["start_time"])
            ).total_seconds() // 60
        )
        if duration > 0:
            alternatives = find_alternative_slots(db, AlternativeSlotsIn(
                date=filters["date"],
                duration_minutes=duration,
                participant_count=filters["participant_count"],
                faculty=filters["faculty"],
                building=filters["building"],
                facilities=filters["facilities"],
                preferred_start_time=filters["start_time"],
                search_days=7,
                slot_step_minutes=30,
                limit=5,
            ))

    if rooms:
        response_message = f"Saya menemukan {len(rooms)} ruangan yang sesuai dengan kriteria pencarian."
        if filters["date"] and filters["start_time"] and filters["end_time"]:
            response_message += " Slot tersebut lolos pemeriksaan ketersediaan saat ini."
    elif alternatives:
        response_message = "Tidak ada ruangan yang tersedia pada slot persis tersebut. Berikut beberapa alternatif tanggal, waktu, atau ruangan."
    else:
        response_message = "Belum ada ruangan yang cocok. Coba ubah fakultas, gedung, kapasitas, fasilitas, atau waktu."
    follow_up = []
    if not (filters["date"] and filters["start_time"] and filters["end_time"]):
        follow_up.append("Untuk mengecek ketersediaan, kirim tanggal, jam mulai, dan jam selesai.")
    if not filters["min_capacity"]:
        follow_up.append("Berapa jumlah peserta yang akan menggunakan ruangan?")
    room_data = [serialize_room(room) for room in rooms[:10]]
    legacy_filters = {
        "faculty": filters["faculty"],
        "building": filters["building"],
        "min_capacity": filters["min_capacity"],
        "facilities": filters["facilities"],
        "date": filters["date"].isoformat() if filters["date"] else None,
        "start_time": filters["start_time"].isoformat() if filters["start_time"] else None,
        "end_time": filters["end_time"].isoformat() if filters["end_time"] else None,
        "participant_count": filters["participant_count"],
    }
    slots = AssistantChatSlots(
        faculty=filters["faculty"],
        building=filters["building"],
        min_capacity=filters["min_capacity"],
        facilities=filters["facilities"],
        requested_date=filters["date"],
        start_time=filters["start_time"],
        end_time=filters["end_time"],
        participant_count=filters["participant_count"],
        search_terms=filters["search_terms"],
    )
    missing_fields = []
    if not (filters["date"] and filters["start_time"] and filters["end_time"]):
        missing_fields.extend(["date", "start_time", "end_time"])
    if not filters["min_capacity"]:
        missing_fields.append("min_capacity")

    result_type = (
        "ROOMS_FOUND" if room_data
        else "ALTERNATIVE_SLOTS" if alternatives
        else "NO_RESULTS"
    )
    structured_response = AssistantChatResponseData(
        message=response_message,
        conversation_id=None,
        intent="ROOM_SEARCH",
        slots=slots,
        confidence=None,
        missing_fields=missing_fields,
        requires_clarification=bool(follow_up),
        clarification_message=follow_up[0] if follow_up else None,
        result_type=result_type,
        requires_confirmation=False,
        data=AssistantChatStructuredData(
            rooms=room_data,
            alternative_slots=alternatives,
            filters=slots,
        ),
        engine="RULE_BASED",
        filters=legacy_filters,
        rooms=room_data,
        alternative_slots=alternatives,
        follow_up_questions=follow_up,
        reservation_action="NOT_CREATED",
        privacy="Pesan tidak disimpan sebagai riwayat percakapan dan tidak dikirim ke penyedia AI eksternal.",
    )
    return success(structured_response.model_dump(mode="json", by_alias=True), "Room assistant response generated")
