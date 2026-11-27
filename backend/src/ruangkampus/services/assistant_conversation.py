from __future__ import annotations

import re
from datetime import date, datetime, time, timedelta, timezone
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ruangkampus.models import AssistantConversation

CONVERSATION_TTL_MINUTES = 30
_STATE_VERSION = 1
_SLOT_FIELDS = (
    "faculty",
    "building",
    "min_capacity",
    "facilities",
    "date",
    "start_time",
    "end_time",
    "participant_count",
    "search_terms",
)
_RESET_PHRASES = (
    "mulai dari awal",
    "mulai ulang",
    "reset pencarian",
    "hapus pencarian",
    "ganti topik",
)

_NEW_SEARCH_PATTERN = re.compile(
    r"\b(?:cari(?:kan|in)?|carikan|mencari|nyari)\b.{0,50}"
    r"\b(?:ruang(?:an)?|rgn|room|lab|laboratorium)\b",
    flags=re.IGNORECASE,
)


def is_new_room_search_request(message: str) -> bool:
    """Detect an explicit new search request, not an elliptical filter follow-up."""
    normalized = " ".join(message.casefold().split())
    return bool(_NEW_SEARCH_PATTERN.search(normalized))




def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def load_or_create_conversation(
    db: Session,
    *,
    user_id: UUID,
    requested_id: UUID | None,
) -> AssistantConversation:
    """Load a non-expired user-owned conversation or create a fresh opaque ID."""
    now = utc_now()
    conversation = None
    rotate_id = False
    if requested_id is not None:
        conversation = db.scalar(
            select(AssistantConversation).where(AssistantConversation.id == requested_id)
        )
        if conversation is not None and conversation.user_id != user_id:
            raise HTTPException(status_code=404, detail="Conversation not found")
        if conversation is not None and _as_utc(conversation.expires_at) <= now:
            db.delete(conversation)
            db.flush()
            conversation = None
            rotate_id = True

    if conversation is None:
        conversation_values = {
            "user_id": user_id,
            "state": {"version": _STATE_VERSION, "slots": {}},
            "expires_at": now + timedelta(minutes=CONVERSATION_TTL_MINUTES),
        }
        if requested_id is not None and not rotate_id:
            conversation_values["id"] = requested_id
        conversation = AssistantConversation(**conversation_values)
        db.add(conversation)
        db.flush()
    else:
        conversation.expires_at = now + timedelta(minutes=CONVERSATION_TTL_MINUTES)
        conversation.updated_at = now

    # Opportunistically purge this user's expired rows; state retention is bounded by inactivity TTL.
    db.execute(
        delete(AssistantConversation).where(
            AssistantConversation.user_id == user_id,
            AssistantConversation.expires_at <= now,
        )
    )
    return conversation


def merge_room_slots(
    current: dict,
    previous_state: dict | None,
    *,
    message: str,
    explicitly_supplied: set[str] | None = None,
) -> dict:
    """Fill omitted search slots from the same user's short-lived context only."""
    merged = dict(current)
    text = " ".join(message.casefold().split())
    if any(phrase in text for phrase in _RESET_PHRASES):
        return merged

    prior = previous_state.get("slots", {}) if isinstance(previous_state, dict) else {}
    if not isinstance(prior, dict):
        return merged
    explicit = explicitly_supplied or set()
    question_suffix = bool(re.search(r"\b(?:ga|gak|nggak|enggak|tidak)\s*[?!.,]*$", text))
    yes_no_question = bool(re.search(r"\b(?:ada|apakah|punya)\b", text))
    has_negation = bool(re.search(r"\b(tidak|bukan|jangan|tanpa|kecuali)\b", text)) and not (
        question_suffix and yes_no_question
    )

    # A changed date starts a different availability window. Do not silently carry
    # the previous date's hours into the new day, but keep stable room criteria.
    current_date = merged.get("date")
    previous_date = prior.get("date")
    date_changed = False
    if current_date is not None and previous_date is not None:
        try:
            current_value = date.fromisoformat(current_date) if isinstance(current_date, str) else current_date
            previous_value = date.fromisoformat(previous_date) if isinstance(previous_date, str) else previous_date
            date_changed = current_value != previous_value
        except (TypeError, ValueError):
            date_changed = False

    # Facility mentions in follow-up questions are additive by default:
    # "ada proyektor?" should keep previously required AC and Wi-Fi.
    # A clear replacement phrase ("ganti fasilitas", "cukup Wi-Fi saja") replaces
    # the previous list. Negated follow-ups never re-add old positive facilities.
    current_facilities = merged.get("facilities") or []
    previous_facilities = prior.get("facilities") or []
    asks_to_replace_facilities = bool(
        re.search(r"\b(?:ganti|ubah|cukup|hanya)\b", text)
        or re.search(r"\b(?:saja|aja)\b", text)
    )
    if current_facilities and previous_facilities and not has_negation and not asks_to_replace_facilities:
        combined: list[str] = []
        seen: set[str] = set()
        for facility in [*current_facilities, *previous_facilities]:
            label = str(facility).strip()
            key = label.casefold()
            if label and key not in seen:
                combined.append(label)
                seen.add(key)
        merged["facilities"] = combined

    for field in _SLOT_FIELDS:
        if field == "facilities" and current_facilities:
            continue
        if date_changed and field in {"start_time", "end_time"}:
            continue
        value = merged.get(field)
        empty = value is None or value == [] or (field == "search_terms" and not value)
        if field == "participant_count":
            empty = field not in explicit and value == 1
        if not empty or field in explicit:
            continue
        if has_negation and field in {"faculty", "building", "facilities"}:
            continue
        candidate = prior.get(field)
        if candidate is not None and candidate != []:
            try:
                if field == "date" and isinstance(candidate, str):
                    candidate = date.fromisoformat(candidate)
                elif field in {"start_time", "end_time"} and isinstance(candidate, str):
                    candidate = time.fromisoformat(candidate)
            except ValueError:
                continue
            merged[field] = candidate
    return merged


def save_conversation_state(
    db: Session,
    conversation: AssistantConversation,
    *,
    intent: str,
    slots: dict,
    room_ids: list[UUID | str] | None = None,
) -> None:
    """Persist bounded search slots and verified public room IDs, never raw chat text."""
    safe_slots: dict = {}
    for field in _SLOT_FIELDS:
        value = slots.get(field)
        if value is None:
            safe_slots[field] = None
        elif field in {"facilities", "search_terms"}:
            limit = 25 if field == "facilities" else 5
            safe_slots[field] = [str(item)[:80] for item in value[:limit] if item]
        elif hasattr(value, "isoformat"):
            safe_slots[field] = value.isoformat()
        elif isinstance(value, (str, int, float, bool)):
            safe_slots[field] = value if not isinstance(value, str) else value[:160]

    stored_state = {"version": _STATE_VERSION, "slots": safe_slots}
    candidate_ids = (
        room_ids
        if room_ids is not None
        else conversation.state.get("room_ids", [])
        if isinstance(conversation.state, dict)
        else []
    )
    if not isinstance(candidate_ids, list):
        candidate_ids = []
    verified_room_ids: list[str] = []
    for item in candidate_ids[:10]:
        try:
            value = str(UUID(str(item)))
        except (TypeError, ValueError, AttributeError):
            continue
        if value not in verified_room_ids:
            verified_room_ids.append(value)
    if verified_room_ids:
        stored_state["room_ids"] = verified_room_ids

    conversation.state = stored_state
    conversation.last_intent = intent[:40]
    conversation.updated_at = utc_now()
    conversation.expires_at = conversation.updated_at + timedelta(minutes=CONVERSATION_TTL_MINUTES)
    db.add(conversation)
