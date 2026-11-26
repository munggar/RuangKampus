from __future__ import annotations

import re
from datetime import date, datetime, time, timedelta, timezone
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
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
    has_negation = bool(re.search(r"\b(tidak|bukan|jangan|tanpa|kecuali)\b", text))

    for field in _SLOT_FIELDS:
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
) -> None:
    """Persist bounded structured slots; never persist raw or normalized chat text."""
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
    conversation.state = {"version": _STATE_VERSION, "slots": safe_slots}
    conversation.last_intent = intent[:40]
    conversation.updated_at = utc_now()
    conversation.expires_at = conversation.updated_at + timedelta(minutes=CONVERSATION_TTL_MINUTES)
    db.add(conversation)
