import re
from datetime import date, datetime, time, timedelta
from uuid import UUID
from fastapi import APIRouter, Depends
from sqlalchemy import String, func, or_, select
from sqlalchemy.orm import Session, joinedload

from ruangkampus.config import get_settings
from ruangkampus.database import get_db
from ruangkampus.dependencies import require_student
from ruangkampus.models import AssistantLearningFeedback, Reservation, Room, User
from ruangkampus.responses import success
from ruangkampus.schemas import (
    AlternativeSlotsIn,
    AssistantChatIn,
    AssistantFeedbackIn,
    AssistantChatResponseData,
    AssistantChatSlots,
    AssistantChatStructuredData,
    serialize_room,
)
from ruangkampus.services.assistant_catalog import FACILITY_TERMS, build_assistant_data_catalog
from ruangkampus.services.availability import check_room_availability, campus_today
from ruangkampus.services.indonesian_normalizer import (
    PARSER_STOP_WORDS,
    find_positive_catalog_values,
    find_positive_facility_filters,
    normalize_indonesian_message,
)
from ruangkampus.services.assistant_intent import (
    IntentDetection,
    detect_assistant_intent,
    is_room_operation_candidate,
)
from ruangkampus.services.assistant_ai_fallback import interpret_with_ai_fallback
from ruangkampus.services.assistant_ai_response import generate_grounded_assistant_message
from ruangkampus.services.assistant_confidence import evaluate_rule_confidence
from ruangkampus.services.assistant_function_registry import get_assistant_function
from ruangkampus.services.assistant_response import (
    compose_intent_response,
    compose_reservation_result,
    compose_room_detail,
    compose_search_result,
)
from ruangkampus.services.assistant_analytics import record_assistant_outcome
from ruangkampus.services.assistant_adaptive_learning import get_adaptive_learning_preferences
from ruangkampus.services.assistant_conversation import (
    load_or_create_conversation,
    merge_room_slots,
    save_conversation_state,
)


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
MONTHS = {
    "januari": 1, "jan": 1,
    "februari": 2, "feb": 2,
    "maret": 3, "mar": 3,
    "april": 4, "apr": 4,
    "mei": 5, "may": 5,
    "juni": 6, "jun": 6,
    "juli": 7, "jul": 7,
    "agustus": 8, "agu": 8, "aug": 8,
    "september": 9, "sep": 9,
    "oktober": 10, "okt": 10, "oct": 10,
    "november": 11, "nov": 11,
    "desember": 12, "des": 12, "dec": 12,
}


def _parse_date_from_message(message: str) -> date | None:
    """Parse explicit Indonesian/ISO dates and common relative campus dates."""
    iso_match = re.search(r"\b(20\d{2}-\d{2}-\d{2})\b", message)
    if iso_match:
        try:
            return date.fromisoformat(iso_match.group(1))
        except ValueError:
            return None

    named_match = re.search(
        r"\b(\d{1,2})\s+("
        + "|".join(sorted(MONTHS, key=len, reverse=True))
        + r")\s+(20\d{2})\b",
        message,
        flags=re.IGNORECASE,
    )
    if named_match:
        try:
            return date(
                int(named_match.group(3)),
                MONTHS[named_match.group(2).casefold()],
                int(named_match.group(1)),
            )
        except ValueError:
            return None

    numeric_match = re.search(r"\b(\d{1,2})[/-](\d{1,2})[/-](20\d{2})\b", message)
    if numeric_match:
        try:
            return date(
                int(numeric_match.group(3)),
                int(numeric_match.group(2)),
                int(numeric_match.group(1)),
            )
        except ValueError:
            return None

    today = campus_today()
    if re.search(r"\bbesok\b", message):
        return today + timedelta(days=1)
    if re.search(r"\blusa\b", message):
        return today + timedelta(days=2)

    for label, weekday in WEEKDAYS.items():
        if re.search(rf"\b{label}\b", message):
            delta = (weekday - today.weekday()) % 7
            return today + timedelta(days=delta or 7)
    return None


STOP_WORDS = {
    "saya", "mau", "ingin", "tolong", "carikan", "cari", "ruangan", "ruang",
    "untuk", "orang", "peserta", "kapasitas", "di", "pada", "hari", "tanggal",
    "dengan", "yang", "ada", "buat", "booking", "reservasi", "peminjaman",
    "gedung", "fakultas", "dan", "atau", "butuh", "bisa", "apakah",
    "cek", "benar", "wajib", "januari", "februari", "maret", "april", "mei",
    "juni", "juli", "agustus", "september", "oktober", "november", "desember",
    "jan", "feb", "mar", "apr", "may", "jun", "jul", "agu", "aug", "sep", "okt", "oct", "nov", "des", "dec",
}
STOP_WORDS.update(PARSER_STOP_WORDS)

SEARCH_INTENTS = {"ROOM_SEARCH", "ROOM_AVAILABILITY", "ALTERNATIVE_SLOTS"}
_CONTEXTUAL_AVAILABILITY_FOLLOW_UPS = (
    "masih ada yang kosong",
    "ada yang kosong",
    "masih kosong",
    "yang kosong",
    "masih tersedia",
    "ada yang tersedia",
    "masih ada",
)


def _is_contextual_availability_follow_up(message: str) -> bool:
    normalized = " ".join(message.casefold().split())
    return any(
        re.search(rf"(?<![a-z0-9]){re.escape(phrase)}(?![a-z0-9])", normalized)
        for phrase in _CONTEXTUAL_AVAILABILITY_FOLLOW_UPS
    )


def _missing_availability_fields(filters: dict) -> list[str]:
    fields = (
        ("date", "date"),
        ("start_time", "start_time"),
        ("end_time", "end_time"),
    )
    return [name for key, name in fields if filters.get(key) is None]


def _availability_clarification(filters: dict) -> str:
    missing = set(_missing_availability_fields(filters))
    if missing == {"start_time", "end_time"} and filters.get("date") is not None:
        return "Sip, tanggalnya udah gue catat. Lu mau mulai dan selesai jam berapa? Contoh: 09.00–11.00."
    if missing == {"date"}:
        return "Jamnya udah gue catat. Lu mau pakai ruang tanggal berapa?"
    if missing == {"start_time"}:
        return "Jam selesai udah gue catat. Mulainya jam berapa?"
    if missing == {"end_time"}:
        return "Jam mulai udah gue catat. Selesainya jam berapa?"
    return "Tanggal dan jamnya kapan, nih? Kirim sekalian, misalnya besok 09.00–11.00."


def _parse_time(value: str | time) -> time:
    return value if isinstance(value, time) else time.fromisoformat(value)


def _clock_time(hour: str, minute: str | None, period: str | None) -> time | None:
    parsed_hour = int(hour)
    parsed_minute = int(minute or 0)
    if period in {"pagi", "malam"} and parsed_hour == 12:
        parsed_hour = 0
    elif period in {"siang", "sore", "malam"} and parsed_hour < 12:
        parsed_hour += 12
    return time(parsed_hour, parsed_minute) if 0 <= parsed_hour <= 23 else None


def _parse_time_range_follow_up(message: str) -> tuple[time, time] | None:
    """Parse compact ranges such as 'jam 10 - 12' or '10.00–12.00 siang'."""
    match = re.search(
        r"(?<!\d)(?:(?:jam|pukul)\s*)?"
        r"([01]?\d|2[0-3])(?:[:.]([0-5]\d))?\s*(pagi|siang|sore|malam)?\s*"
        r"(?:-|–|—|s/d|sd|sampai|hingga|to)\s*"
        r"(?:(?:jam|pukul)\s*)?([01]?\d|2[0-3])(?:[:.]([0-5]\d))?\s*"
        r"(pagi|siang|sore|malam)?(?!\d)",
        message.casefold(),
    )
    if not match:
        return None
    start_period = match.group(3) or match.group(6)
    end_period = match.group(6) or match.group(3)
    start_time = _clock_time(match.group(1), match.group(2), start_period)
    end_time = _clock_time(match.group(4), match.group(5), end_period)
    if start_time is None or end_time is None or end_time <= start_time:
        return None
    return start_time, end_time


def _parse_time_only_follow_up(message: str) -> time | None:
    """Parse a short time-only reply such as 'jam 10' or 'sampai jam 12 siang'."""
    match = re.fullmatch(
        r"\s*(?:(?:sampai|hingga|sd|s/d)\s*)?(?:(?:jam|pukul)\s*)?"
        r"([01]?\d|2[0-3])(?:[:.]([0-5]\d))?\s*"
        r"(pagi|siang|sore|malam)?[.!?\s]*",
        message.casefold(),
    )
    if not match:
        return None
    return _clock_time(match.group(1), match.group(2), match.group(3))


def _apply_contextual_end_time_follow_up(filters: dict, conversation, message: str) -> bool:
    """Merge a time-only follow-up with the current user's previous availability request."""
    if conversation.last_intent not in SEARCH_INTENTS:
        return False
    previous = conversation.state.get("slots", {}) if isinstance(conversation.state, dict) else {}
    if not isinstance(previous, dict):
        return False
    previous_date = previous.get("date")
    if not previous_date:
        return False
    try:
        requested_date = date.fromisoformat(previous_date) if isinstance(previous_date, str) else previous_date
    except (TypeError, ValueError):
        return False
    if not isinstance(requested_date, date):
        return False

    # A complete range fills both clock slots, even when the first message only
    # supplied a day ("ruangan kosong hari Senin").
    time_range = _parse_time_range_follow_up(message)
    if time_range is not None:
        filters["date"] = filters.get("date") or requested_date
        filters["start_time"], filters["end_time"] = time_range
        return True

    single_time = _parse_time_only_follow_up(message)
    if single_time is None:
        return False

    filters["date"] = filters.get("date") or requested_date
    previous_start = previous.get("start_time")
    previous_end = previous.get("end_time")
    if previous_start is None and previous_end is None:
        filters["start_time"] = single_time
        filters["end_time"] = None
        return True

    if previous_start is not None and previous_end is None:
        try:
            start_time = _parse_time(previous_start)
        except (TypeError, ValueError):
            return False
        if single_time <= start_time:
            return False
        filters["start_time"] = start_time
        filters["end_time"] = single_time
        return True
    return False

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
        aliases = FACILITY_TERMS.get(facility.casefold(), (facility,))
        facility_conditions = [
            func.lower(Room.facilities.cast(String)).like(f"%{alias.casefold()}%")
            for alias in aliases
        ]
        stmt = stmt.where(or_(*facility_conditions))
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
        search_terms=request.search_terms,
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
                    # Do not label the exact requested date/time as an alternative.
                    if (
                        day_offset == 0
                        and request.preferred_start_time is not None
                        and start_time == request.preferred_start_time
                    ):
                        current += timedelta(minutes=request.slot_step_minutes)
                        continue
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


def _parse_message_filters(
    db: Session,
    payload: AssistantChatIn,
    catalog: dict | None = None,
) -> dict:
    message = payload.message.casefold()
    catalog = catalog if catalog is not None else build_assistant_data_catalog(db)
    min_capacity = payload.min_capacity
    if min_capacity is None:
        capacity_match = re.search(
            r"\b(\d{1,4})\s*(?:orang|org|peserta|pax|people|person|mahasiswa|mhs|students?)\b",
            message,
        )
        if capacity_match is None:
            capacity_match = re.search(
                r"\b(?:muat|kapasitas(?:\s+minimal)?|minimal)\s+(\d{1,4})\b",
                message,
            )
        if capacity_match:
            min_capacity = int(capacity_match.group(1))

    building = payload.building
    if building is None:
        building_matches = find_positive_catalog_values(message, catalog.get("buildings", []))
        if len(building_matches) == 1:
            building = building_matches[0]

    faculty = payload.faculty
    if faculty is None:
        faculty_matches = find_positive_catalog_values(message, catalog.get("faculties", []))
        if len(faculty_matches) == 1:
            faculty = faculty_matches[0]

    # Only facilities observed in active room data can become canonical filters.
    # A facility mentioned in a negated clause is retained in text but not treated as required.
    facilities = list(payload.facilities)
    if not facilities:
        facilities = find_positive_facility_filters(message, catalog)

    requested_date = payload.requested_date
    if requested_date is None:
        requested_date = _parse_date_from_message(message)

    start_time, end_time = payload.start_time, payload.end_time
    if start_time is None and end_time is None:
        time_range = _parse_time_range_follow_up(message)
        if time_range is not None:
            start_time, end_time = time_range
        else:
            single_time = re.search(
                r"\b(?:jam|pukul)\s*(\d{1,2})(?:[:.]([0-5]\d))?\s*(pagi|siang|sore|malam)?\b",
                message,
            )
            if single_time:
                parsed = _clock_time(single_time.group(1), single_time.group(2), single_time.group(3))
                if parsed is not None:
                    start_time = parsed
    # An activity's purpose is not always a room-name/description filter.
    # Keep explicit types ("ruang rapat") searchable but ignore "buat rapat".
    search_message = re.sub(
        r"\b(?:buat|untuk|keperluan)\s+(?:rapat|meeting|diskusi|brainstorming|seminar|presentasi|kuliah|organisasi|acara|kegiatan)\b",
        " ",
        message,
    )
    message_tokens = re.findall(r"[a-z0-9-]+", search_message)
    expanded_tokens = []
    for token in message_tokens:
        if "-" in token and not any(character.isdigit() for character in token):
            expanded_tokens.extend(token.split("-"))
        else:
            expanded_tokens.append(token)
    tokens = [
        token for token in expanded_tokens
        if len(token) >= 3 and token not in STOP_WORDS and not token.isdigit()
    ]

    # Remove all catalogue facility and faculty/building labels from free-text terms.
    # This is especially important for negated clauses: "jangan pakai proyektor"
    # must not become a positive room-description search for "proyektor".
    metadata_tokens: set[str] = set()
    for entry in [*catalog.get("faculties", []), *catalog.get("buildings", [])]:
        for value in [entry.get("value"), *entry.get("source_values", [])]:
            if isinstance(value, str):
                metadata_tokens.update(re.findall(r"[a-z0-9-]+", value.casefold()))
    for entry in catalog.get("facilities", []):
        values = [
            entry.get("canonical_name"),
            *entry.get("source_values", []),
            *entry.get("aliases", []),
        ]
        for value in values:
            if isinstance(value, str):
                metadata_tokens.update(re.findall(r"[a-z0-9-]+", value.casefold()))
    for canonical, aliases in FACILITY_TERMS.items():
        for value in (canonical, *aliases):
            metadata_tokens.update(re.findall(r"[a-z0-9-]+", value.casefold()))
    tokens = [
        token for token in tokens
        if token not in metadata_tokens
        and not any(part in metadata_tokens for part in re.split(r"[-._/]", token))
    ]
    if building:
        tokens = [token for token in tokens if token not in re.findall(r"[a-z0-9-]+", building.casefold())]
    if faculty:
        tokens = [token for token in tokens if token not in re.findall(r"[a-z0-9-]+", faculty.casefold())]

    return {
        "faculty": faculty,
        "building": building,
        "min_capacity": min_capacity,
        "facilities": facilities,
        "date": requested_date,
        "start_time": start_time,
        "end_time": end_time,
        "participant_count": (
            payload.participant_count
            if "participant_count" in payload.model_fields_set
            else min_capacity or payload.participant_count
        ),
        "search_terms": list(dict.fromkeys(tokens))[:5],
    }


@router.post("/assistant/feedback")
def assistant_feedback(
    payload: AssistantFeedbackIn,
    user: User = Depends(require_student),
    db: Session = Depends(get_db),
):
    """Store only an authenticated student's explicit, allowlisted feedback signal."""
    db.add(AssistantLearningFeedback(
        user_id=user.id,
        intent=payload.intent,
        rating=payload.rating,
        reason_code=payload.reason_code,
    ))
    db.commit()
    return success({"recorded": True}, "Assistant feedback recorded")


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


def _assistant_empty_slots(payload: AssistantChatIn) -> AssistantChatSlots:
    return AssistantChatSlots(
        faculty=payload.faculty,
        building=payload.building,
        min_capacity=payload.min_capacity,
        facilities=payload.facilities,
        requested_date=payload.requested_date,
        start_time=payload.start_time,
        end_time=payload.end_time,
        participant_count=payload.participant_count,
        search_terms=[],
    )


def _assistant_legacy_filters(slots: AssistantChatSlots) -> dict:
    return {
        "faculty": slots.faculty,
        "building": slots.building,
        "min_capacity": slots.min_capacity,
        "facilities": slots.facilities,
        "date": slots.requested_date.isoformat() if slots.requested_date else None,
        "start_time": slots.start_time.isoformat() if slots.start_time else None,
        "end_time": slots.end_time.isoformat() if slots.end_time else None,
        "participant_count": slots.participant_count,
    }


def _owned_reservation_summaries(db: Session, user: User, intent: str) -> list[dict]:
    """Read only the authenticated student's own reservations."""
    stmt = (
        select(Reservation)
        .options(joinedload(Reservation.room))
        .where(Reservation.user_id == user.id)
        .order_by(Reservation.submitted_at.desc())
        .limit(5)
    )
    records = db.scalars(stmt).unique().all()
    return [
        {
            "id": str(item.id),
            "room_name": item.room.room_name,
            "building": item.room.building,
            "date": item.reservation_date.isoformat(),
            "start_time": item.start_time.isoformat(),
            "end_time": item.end_time.isoformat(),
            "participant_count": item.participant_count,
            "status": item.status,
            "purpose": item.purpose,
        }
        for item in records
    ]


def _room_detail_matches(catalog: dict, normalized_text: str) -> list[dict]:
    """Resolve room names/codes only from the active-room catalogue."""
    matches = []
    for entry in catalog.get("rooms", []):
        if not isinstance(entry, dict):
            continue
        for label in (entry.get("room_code"), entry.get("room_name")):
            if not isinstance(label, str) or not label.strip():
                continue
            pattern = rf"(?<![a-z0-9]){re.escape(label.casefold())}(?![a-z0-9])"
            if re.search(pattern, normalized_text.casefold()):
                matches.append(entry)
                break
    return matches


def _intent_response_message(intent: str, response_variant: str | None = None) -> str:
    return compose_intent_response(intent, response_variant)


def _references_previous_room_result(message: str) -> bool:
    normalized = " ".join(message.casefold().split())
    phrases = (
        "ruangan itu", "ruang itu", "ruangannya", "ruangan tadi",
        "ruang tadi", "rekomendasi tadi", "direkomendasikan",
        "kenapa ruangan", "kenapa ruang", "alasan rekomendasi",
        "pilihan tadi", "kandidat tadi", "hasil pencarian tadi",
        "yang tadi kamu rekomendasikan", "yang kamu rekomendasikan", "yang tadi lu rekomendasikan", "yang lu rekomendasikan",
    )
    return any(
        re.search(rf"(?<![a-z0-9]){re.escape(phrase)}(?![a-z0-9])", normalized)
        for phrase in phrases
    )


def _verified_previous_room_context(db: Session, conversation) -> list[dict]:
    state = conversation.state if isinstance(conversation.state, dict) else {}
    candidates = state.get("room_ids", [])
    room_ids: list[UUID] = []
    for item in candidates[:10] if isinstance(candidates, list) else []:
        try:
            room_id = UUID(str(item))
        except (TypeError, ValueError, AttributeError):
            continue
        if room_id not in room_ids:
            room_ids.append(room_id)
    if not room_ids:
        return []
    records = db.scalars(
        select(Room).where(
            Room.id.in_(room_ids),
            Room.deleted_at.is_(None),
            Room.room_status == "ACTIVE",
        )
    ).all()
    by_id = {room.id: room for room in records}
    return [serialize_room(by_id[room_id]) for room_id in room_ids if room_id in by_id]


def _maybe_generate_ai_message(
    *,
    message: str,
    intent: str,
    deterministic_message: str,
    filters: dict,
    rooms: list[dict] | None = None,
    alternative_slots: list[dict] | None = None,
    follow_up_questions: list[str] | None = None,
    availability_checked: bool = False,
    db: Session | None = None,
    user_id: UUID | None = None,
    context_messages: list[dict[str, str]] | None = None,
) -> tuple[str, bool]:
    settings = get_settings()
    adaptive_preferences = (
        get_adaptive_learning_preferences(db, user_id)
        if settings.assistant_ai_enabled and db is not None and user_id is not None
        else []
    )
    generated = generate_grounded_assistant_message(
        message=message,
        intent=intent,
        deterministic_message=deterministic_message,
        filters=filters,
        rooms=rooms or [],
        alternative_slots=alternative_slots or [],
        follow_up_questions=follow_up_questions or [],
        availability_checked=availability_checked,
        settings=settings,
        adaptive_preferences=adaptive_preferences,
        context_messages=context_messages,
    )
    return (generated, True) if generated else (deterministic_message, False)


def _intent_only_response(
    payload: AssistantChatIn,
    normalization,
    detection,
    *,
    missing_fields: list[str] | None = None,
    conversation_id=None,
    confidence: float | None = None,
    confidence_basis: str = "RULE_HEURISTIC",
    engine: str = "RULE_BASED",
    privacy_message: str | None = None,
    message_override: str | None = None,
    rooms: list[dict] | None = None,
    provider_rooms: list[dict] | None = None,
    reservations: list[dict] | None = None,
    result_type: str = "NO_RESULTS",
    requires_clarification: bool | None = None,
    ai_fallback_used: bool = False,
    slots_override: AssistantChatSlots | None = None,
    availability_checked: bool = False,
    db: Session | None = None,
    user_id: UUID | None = None,
):
    slots = slots_override or _assistant_empty_slots(payload)
    follow_up = [detection.clarification_message] if detection.clarification_message else []
    base_message = message_override or detection.clarification_message or _intent_response_message(detection.intent, detection.response_variant)
    if ai_fallback_used:
        final_message, ai_response_used = base_message, False
    else:
        final_message, ai_response_used = _maybe_generate_ai_message(
            message=payload.message,
            intent=detection.intent,
            deterministic_message=base_message,
            filters=_assistant_legacy_filters(slots),
            rooms=provider_rooms if provider_rooms is not None else (rooms or []),
            follow_up_questions=follow_up,
            availability_checked=availability_checked,
            db=db,
            user_id=user_id,
            context_messages=[item.model_dump() for item in payload.context],
        )
    engine_value = "HYBRID" if ai_fallback_used or ai_response_used else engine
    privacy_value = privacy_message or (
        "Pesan saat ini dan ringkasan fakta ruangan yang relevan dikirim ke penyedia AI yang dikonfigurasi. "
        "Maksimal sepuluh pesan terakhir dari tab percakapan dapat ikut dikirim sebagai konteks dan tidak disimpan sebagai isi chat oleh backend. "
        "Backend hanya menyimpan slot pencarian terstruktur dan ID kandidat terverifikasi selama maksimal 30 menit, bukan isi chat mentah. Identitas akun dan data reservasi pribadi tidak dikirim. Umpan balik manual hanya menyimpan penilaian dan kode alasan."
        if ai_response_used else
        "Pesan saat ini dikirim ke penyedia AI hanya untuk interpretasi intent. Riwayat percakapan, "
        "identitas akun, dan data reservasi pribadi tidak dikirim. Umpan balik manual hanya menyimpan penilaian dan kode alasan."
        if ai_fallback_used else
        "Pesan asli tidak disimpan. Slot pencarian terstruktur disimpan sementara "
        "selama maksimal 30 menit. Umpan balik manual hanya menyimpan penilaian dan kode alasan."
    )
    structured_response = AssistantChatResponseData(
        message=final_message,
        conversation_id=conversation_id,
        intent=detection.intent,
        slots=slots,
        confidence=confidence,
        confidence_basis=confidence_basis if confidence is not None else None,
        missing_fields=missing_fields or [],
        requires_clarification=(
            detection.requires_clarification if requires_clarification is None else requires_clarification
        ),
        clarification_message=detection.clarification_message,
        result_type=result_type,
        requires_confirmation=False,
        data=AssistantChatStructuredData(
            rooms=rooms or [],
            alternative_slots=[],
            reservations=reservations or [],
            filters=slots,
        ),
        normalization=normalization,
        engine=engine_value,
        filters=_assistant_legacy_filters(slots),
        rooms=rooms or [],
        alternative_slots=[],
        follow_up_questions=follow_up,
        reservation_action="NOT_CREATED",
        privacy=privacy_value,
    )
    record_assistant_outcome(
        intent=detection.intent,
        matched_rule=detection.matched_rule,
        confidence=confidence,
        confidence_basis=confidence_basis,
        result_type=result_type,
        requires_clarification=structured_response.requires_clarification,
        ai_fallback_used=ai_fallback_used or ai_response_used,
    )
    return success(
        structured_response.model_dump(mode="json", by_alias=True),
        "Assistant intent classified",
    )


@router.post("/assistant/chat")
def room_assistant_chat(
    payload: AssistantChatIn,
    user: User = Depends(require_student),
    db: Session = Depends(get_db),
):
    conversation = load_or_create_conversation(
        db, user_id=user.id, requested_id=payload.conversation_id
    )
    catalog = build_assistant_data_catalog(db)
    normalization = normalize_indonesian_message(payload.message, catalog)
    normalized_payload = payload.model_copy(update={"message": normalization.parser_text})
    filters = _parse_message_filters(db, normalized_payload, catalog)
    _apply_contextual_end_time_follow_up(
        filters,
        conversation,
        normalization.parser_text,
    )

    explicit_fields = set(payload.model_fields_set)
    if "requested_date" in explicit_fields:
        explicit_fields.add("date")
    has_structured_filters = any((
        filters["faculty"], filters["building"], filters["min_capacity"],
        filters["facilities"], filters["date"], filters["start_time"],
        filters["end_time"], payload.faculty, payload.building,
        payload.min_capacity, payload.facilities,
    ))
    has_complete_availability_window = bool(
        filters["date"] and filters["start_time"] and filters["end_time"]
    )
    detection = detect_assistant_intent(
        normalization.normalized_text,
        catalog,
        has_structured_room_filters=has_structured_filters,
        has_complete_availability_window=has_complete_availability_window,
    )
    contextual_followup_used = False
    if (
        detection.intent == "OUT_OF_SCOPE"
        and conversation.last_intent in SEARCH_INTENTS
        and _is_contextual_availability_follow_up(normalization.parser_text)
    ):
        detection = IntentDetection(
            intent="ROOM_AVAILABILITY",
            matched_rule="CONTEXTUAL_AVAILABILITY_FOLLOW_UP",
            requires_clarification=True,
        )
        contextual_followup_used = True

    ai_fallback_used = False
    if (
        detection.intent == "OUT_OF_SCOPE"
        and detection.matched_rule not in {
            "GENERAL_REASONING_REQUEST",
            "HYPOTHETICAL_REASONING_REQUEST",
        }
        and is_room_operation_candidate(normalization.parser_text)
    ):
        interpretation = interpret_with_ai_fallback(payload.message, catalog, get_settings())
        if interpretation is not None:
            ai_fallback_used = True
            ai_updates = {
                "faculty": interpretation.faculty,
                "building": interpretation.building,
                "min_capacity": interpretation.min_capacity,
                "facilities": interpretation.facilities,
                "requested_date": interpretation.date,
                "start_time": interpretation.start_time,
                "end_time": interpretation.end_time,
                "participant_count": interpretation.participant_count,
            }
            ai_payload = payload.model_copy(update=ai_updates)
            normalized_payload = ai_payload.model_copy(update={"message": normalization.parser_text})
            filters = _parse_message_filters(db, normalized_payload, catalog)
            explicit_fields.update(
                field for field, value in {
                    "faculty": interpretation.faculty,
                    "building": interpretation.building,
                    "min_capacity": interpretation.min_capacity,
                    "facilities": interpretation.facilities,
                    "date": interpretation.date,
                    "start_time": interpretation.start_time,
                    "end_time": interpretation.end_time,
                    "participant_count": interpretation.participant_count,
                }.items() if value is not None and value != []
            )
            has_complete_availability_window = bool(
                filters["date"] and filters["start_time"] and filters["end_time"]
            )
            missing_ai_window = (
                interpretation.intent in {"ROOM_AVAILABILITY", "ALTERNATIVE_SLOTS"}
                and not has_complete_availability_window
            )
            detection = IntentDetection(
                intent=interpretation.intent,
                matched_rule="AI_INTENT_FALLBACK",
                requires_clarification=missing_ai_window,
                clarification_message=(
                    "Untuk memeriksa ketersediaan, sebutkan tanggal, jam mulai, dan jam selesai."
                    if missing_ai_window else None
                ),
            )

    function_spec = get_assistant_function(detection.intent)
    if function_spec is None:
        detection = IntentDetection(
            intent="OUT_OF_SCOPE",
            matched_rule="NO_REGISTERED_FUNCTION",
            requires_clarification=True,
            clarification_message="Maaf, permintaan itu belum tersedia pada asisten RuangKampus.",
        )
        ai_fallback_used = False

    search_intents = SEARCH_INTENTS
    if detection.intent in search_intents:
        filters = merge_room_slots(
            filters,
            conversation.state,
            message=normalization.normalized_text,
            explicitly_supplied=explicit_fields,
        )
        if filters.get("min_capacity") is not None and "participant_count" not in explicit_fields:
            filters["participant_count"] = filters["min_capacity"]
        has_complete_availability_window = bool(
            filters["date"] and filters["start_time"] and filters["end_time"]
        )
        has_structured_filters = any((
            filters["faculty"], filters["building"], filters["min_capacity"],
            filters["facilities"], filters["date"], filters["start_time"],
            filters["end_time"],
        ))
        if ai_fallback_used:
            missing_ai_window = (
                detection.intent in {"ROOM_AVAILABILITY", "ALTERNATIVE_SLOTS"}
                and not has_complete_availability_window
            )
            detection = IntentDetection(
                intent=detection.intent,
                matched_rule="AI_INTENT_FALLBACK",
                requires_clarification=missing_ai_window,
                clarification_message=(
                    "Untuk memeriksa ketersediaan, sebutkan tanggal, jam mulai, dan jam selesai."
                    if missing_ai_window else None
                ),
            )
        elif not contextual_followup_used:
            detection = detect_assistant_intent(
                normalization.normalized_text,
                catalog,
                has_structured_room_filters=has_structured_filters,
                has_complete_availability_window=has_complete_availability_window,
            )

    confidence = evaluate_rule_confidence(
        detection,
        has_catalog_match=bool(filters["faculty"] or filters["building"] or filters["facilities"]),
        has_complete_availability_window=has_complete_availability_window,
    )

    if detection.intent in {"MY_RESERVATIONS", "RESERVATION_STATUS"}:
        reservations = _owned_reservation_summaries(db, user, detection.intent)
        if reservations:
            result_type = "RESERVATIONS_FOUND"
        else:
            result_type = "NO_RESULTS"
        message = compose_reservation_result(
            reservations,
            status_only=detection.intent == "RESERVATION_STATUS",
        )
        response = _intent_only_response(
            payload, normalization, detection,
            conversation_id=conversation.id,
            db=db,
            user_id=user.id,
            confidence=confidence,
            message_override=message,
            reservations=reservations,
            result_type=result_type,
            requires_clarification=False,
        )
        db.commit()
        return response

    if detection.intent == "ROOM_DETAIL":
        matches = _room_detail_matches(catalog, normalization.normalized_text)
        if len(matches) == 1:
            from uuid import UUID

            room = db.scalar(
                select(Room).where(
                    Room.id == UUID(matches[0]["id"]),
                    Room.deleted_at.is_(None),
                    Room.room_status == "ACTIVE",
                )
            )
            if room is not None:
                room_data = [serialize_room(room)]
                message = compose_room_detail(room_data[0])
                response = _intent_only_response(
                    payload, normalization, detection,
                    conversation_id=conversation.id,
                    db=db,
                    user_id=user.id,
                    confidence=confidence,
                    message_override=message,
                    rooms=room_data,
                    result_type="ROOM_DETAILS",
                    requires_clarification=False,
                )
                db.commit()
                return response
        clarify = (
            "Gue nemu beberapa kemungkinan ruang. Sebutin kode ruangnya biar nggak ketuker."
            if len(matches) > 1
            else "Ruangan yang dimaksud belum dapat dipastikan. Sebutkan nama atau kode ruangannya."
        )
        detection = detection.__class__(
            intent=detection.intent,
            matched_rule=detection.matched_rule,
            requires_clarification=True,
            clarification_message=clarify,
            response_variant=detection.response_variant,
        )
        confidence = evaluate_rule_confidence(detection)
        response = _intent_only_response(
            payload, normalization, detection,
            conversation_id=conversation.id,
            db=db,
            user_id=user.id,
            confidence=confidence,
            message_override=clarify,
        )
        db.commit()
        return response

    if detection.intent not in search_intents:
        contextual_room_reference = (
            detection.intent == "OUT_OF_SCOPE"
            and _references_previous_room_result(normalization.parser_text)
        )
        provider_rooms = (
            _verified_previous_room_context(db, conversation)
            if contextual_room_reference else []
        )
        slots_override = None
        if contextual_room_reference:
            prior_explicit_fields = set(payload.model_fields_set)
            if "requested_date" in prior_explicit_fields:
                prior_explicit_fields.add("date")
            prior_filters = merge_room_slots(
                {
                    "faculty": payload.faculty,
                    "building": payload.building,
                    "min_capacity": payload.min_capacity,
                    "facilities": payload.facilities,
                    "date": payload.requested_date,
                    "start_time": payload.start_time,
                    "end_time": payload.end_time,
                    "participant_count": payload.participant_count,
                    "search_terms": [],
                },
                conversation.state,
                message=normalization.normalized_text,
                explicitly_supplied=prior_explicit_fields,
            )
            slots_override = AssistantChatSlots(
                faculty=prior_filters["faculty"],
                building=prior_filters["building"],
                min_capacity=prior_filters["min_capacity"],
                facilities=prior_filters["facilities"],
                requested_date=prior_filters["date"],
                start_time=prior_filters["start_time"],
                end_time=prior_filters["end_time"],
                participant_count=prior_filters["participant_count"],
                search_terms=prior_filters["search_terms"],
            )
        response = _intent_only_response(
            payload, normalization, detection,
            conversation_id=conversation.id,
            db=db,
            user_id=user.id,
            confidence=confidence,
            provider_rooms=provider_rooms,
            slots_override=slots_override,
        )
        db.commit()
        return response

    if detection.intent in {"ROOM_AVAILABILITY", "ALTERNATIVE_SLOTS"} and not has_complete_availability_window:
        pending_slots = AssistantChatSlots(
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
        has_room_criteria = any((
            filters["faculty"], filters["building"], filters["min_capacity"],
            filters["facilities"], filters["search_terms"],
        ))
        partial_rooms = (
            _room_candidates(
                db,
                faculty=filters["faculty"],
                building=filters["building"],
                min_capacity=filters["min_capacity"],
                facilities=filters["facilities"],
                search_terms=filters["search_terms"],
            )
            if has_room_criteria else []
        )
        partial_room_data = [serialize_room(room) for room in partial_rooms[:10]]
        missing_availability_fields = _missing_availability_fields(filters)
        clarification = _availability_clarification(filters)
        detection = IntentDetection(
            intent=detection.intent,
            matched_rule=detection.matched_rule,
            requires_clarification=True,
            clarification_message=clarification,
            response_variant=detection.response_variant,
        )
        partial_message = (
            f"Gue nemu {len(partial_room_data)} kandidat ruang. Jadwalnya belum bisa dipastikan dulu. {clarification}"
            if partial_room_data else
            (
                f"Oke, gue paham lu mau cek ruang kosong. {clarification}"
                if not has_room_criteria else
                f"Belum ada kandidat yang cocok dengan kriteria awal. Coba longgarkan fakultas, gedung, kapasitas, atau fasilitas. {clarification}"
            )
        )
        response = _intent_only_response(
            payload, normalization, detection,
            missing_fields=missing_availability_fields,
            conversation_id=conversation.id,
            db=db,
            user_id=user.id,
            confidence=confidence,
            confidence_basis="AI_FALLBACK" if ai_fallback_used else "RULE_HEURISTIC",
            engine="HYBRID" if ai_fallback_used else "RULE_BASED",
            message_override=partial_message,
            rooms=partial_room_data,
            result_type="ROOMS_FOUND" if partial_room_data else "NO_RESULTS",
            requires_clarification=True,
            privacy_message=(
                "Pesan saat ini yang telah disamarkan dikirim ke penyedia AI hanya untuk interpretasi intent. "
                "Riwayat percakapan, identitas akun, dan data reservasi pribadi tidak dikirim. Umpan balik manual hanya menyimpan penilaian dan kode alasan."
            ) if ai_fallback_used else None,
            ai_fallback_used=ai_fallback_used,
            slots_override=pending_slots,
        )
        save_conversation_state(
            db,
            conversation,
            intent=detection.intent,
            slots=filters,
            room_ids=[room.id for room in partial_rooms[:10]],
        )
        db.commit()
        return response

    has_room_criteria = any((
        filters["faculty"],
        filters["building"],
        filters["min_capacity"],
        filters["facilities"],
        filters["search_terms"],
    ))
    has_effective_search_criteria = (
        has_complete_availability_window
        if detection.intent in {"ROOM_AVAILABILITY", "ALTERNATIVE_SLOTS"}
        else has_room_criteria or has_complete_availability_window
    )

    if detection.intent == "ALTERNATIVE_SLOTS":
        rooms = []
    elif has_effective_search_criteria:
        rooms = _room_candidates(
            db,
            faculty=filters["faculty"],
            building=filters["building"],
            min_capacity=filters["min_capacity"],
            facilities=filters["facilities"],
            search_terms=filters["search_terms"],
        )
    else:
        rooms = []

    if detection.intent in {"ROOM_AVAILABILITY", "ROOM_SEARCH"} and has_complete_availability_window:
        rooms = [
            room for room in rooms
            if check_room_availability(
                db, room, filters["date"], filters["start_time"], filters["end_time"],
                filters["participant_count"],
            ).available
        ]

    alternatives = []
    should_find_alternatives = (
        detection.intent == "ALTERNATIVE_SLOTS"
        or (
            not rooms
            and has_complete_availability_window
            and detection.intent in {"ROOM_SEARCH", "ROOM_AVAILABILITY"}
        )
    )
    if should_find_alternatives and has_complete_availability_window:
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
                search_terms=filters["search_terms"],
                search_days=7,
                slot_step_minutes=30,
                limit=5,
            ))

    response_message = compose_search_result(
        intent=detection.intent,
        room_count=len(rooms),
        alternative_count=len(alternatives),
        has_complete_availability_window=has_complete_availability_window,
        has_effective_search_criteria=has_effective_search_criteria,
    )

    follow_up = []
    if not has_effective_search_criteria:
        follow_up.append(
            "Lu butuh ruang buat kegiatan apa, atau kira-kira berapa orang?"
        )
    elif not has_complete_availability_window:
        follow_up.append(
            "Kapan tanggal dan jam pemakaiannya? Kirim sekaligus, misalnya besok 09.00–11.00."
        )

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
    if detection.intent == "ROOM_SEARCH" and not has_complete_availability_window:
        missing_fields.extend(["date", "start_time", "end_time"])
    if detection.intent == "ROOM_SEARCH" and not filters["min_capacity"]:
        missing_fields.append("min_capacity")

    result_type = (
        "ROOMS_FOUND" if room_data
        else "ALTERNATIVE_SLOTS" if alternatives
        else "NO_RESULTS"
    )
    ai_response_used = False
    if not ai_fallback_used:
        response_message, ai_response_used = _maybe_generate_ai_message(
            message=payload.message,
            intent=detection.intent,
            deterministic_message=response_message,
            filters=legacy_filters,
            rooms=room_data,
            alternative_slots=alternatives,
            follow_up_questions=follow_up,
            availability_checked=has_complete_availability_window,
            db=db,
            user_id=user.id,
            context_messages=[item.model_dump() for item in payload.context],
        )
    structured_response = AssistantChatResponseData(
        message=response_message,
        conversation_id=conversation.id,
        intent=detection.intent,
        slots=slots,
        confidence=confidence,
        confidence_basis="AI_FALLBACK" if ai_fallback_used else "RULE_HEURISTIC",
        missing_fields=missing_fields,
        requires_clarification=bool(follow_up),
        clarification_message=follow_up[0] if follow_up else None,
        result_type=result_type,
        requires_confirmation=False,
        data=AssistantChatStructuredData(
            rooms=room_data,
            alternative_slots=alternatives,
            reservations=[],
            filters=slots,
        ),
        normalization=normalization,
        engine="HYBRID" if ai_fallback_used or ai_response_used else "RULE_BASED",
        filters=legacy_filters,
        rooms=room_data,
        alternative_slots=alternatives,
        follow_up_questions=follow_up,
        reservation_action="NOT_CREATED",
        privacy=(
            "Pesan saat ini dan ringkasan fakta ruangan yang relevan dikirim ke penyedia AI yang dikonfigurasi. "
            "Riwayat percakapan, identitas akun, dan data reservasi pribadi tidak dikirim. Umpan balik manual hanya menyimpan penilaian dan kode alasan."
        ) if ai_response_used else (
            "Pesan saat ini dikirim ke penyedia AI hanya untuk interpretasi intent. Riwayat percakapan, "
            "identitas akun, dan data reservasi pribadi tidak dikirim. Umpan balik manual hanya menyimpan penilaian dan kode alasan."
        ) if ai_fallback_used else "Pesan asli tidak disimpan. Slot pencarian terstruktur dan ID kandidat ruangan terverifikasi disimpan sementara selama maksimal 30 menit. Umpan balik manual hanya menyimpan penilaian dan kode alasan.",
    )
    saved_room_ids = [item["id"] for item in room_data]
    saved_room_ids.extend(
        item["room"]["id"] for item in alternatives if item.get("room", {}).get("id")
    )
    save_conversation_state(
        db,
        conversation,
        intent=detection.intent,
        slots=filters,
        room_ids=list(dict.fromkeys(saved_room_ids))[:10],
    )
    record_assistant_outcome(
        intent=detection.intent,
        matched_rule=detection.matched_rule,
        confidence=confidence,
        confidence_basis="AI_FALLBACK" if ai_fallback_used else "RULE_HEURISTIC",
        result_type=result_type,
        requires_clarification=bool(follow_up),
        ai_fallback_used=ai_fallback_used or ai_response_used,
    )
    db.commit()
    return success(
        structured_response.model_dump(mode="json", by_alias=True),
        "Room assistant response generated",
    )
