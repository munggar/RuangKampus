from __future__ import annotations

import json
import logging
from datetime import date, time
from typing import Any, Literal

import httpx
from pydantic import BaseModel, ConfigDict, Field

from ruangkampus.config import Settings

logger = logging.getLogger(__name__)


class AIIntentInterpretation(BaseModel):
    """Strict, non-transactional intent output accepted from an optional AI provider."""

    model_config = ConfigDict(extra="forbid")

    intent: Literal["ROOM_SEARCH", "ROOM_AVAILABILITY", "ALTERNATIVE_SLOTS"]
    faculty: str | None = Field(default=None, max_length=160)
    building: str | None = Field(default=None, max_length=160)
    min_capacity: int | None = Field(default=None, ge=1, le=10000)
    facilities: list[str] = Field(default_factory=list, max_length=20)
    date: date | None = None
    start_time: time | None = None
    end_time: time | None = None
    participant_count: int = Field(default=1, ge=1, le=10000)


def _catalog_label(value: str | None, entries: list[dict[str, Any]], *, facility: bool = False) -> str | None:
    if value is None:
        return None
    candidate = value.strip().casefold()
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        labels = [
            entry.get("value"),
            entry.get("canonical_name"),
            entry.get("display_name"),
            *entry.get("source_values", []),
            *entry.get("aliases", []),
        ]
        for label in labels:
            if isinstance(label, str) and label.strip().casefold() == candidate:
                if facility:
                    return entry.get("canonical_name") or entry.get("display_name") or label
                return entry.get("value") or label
    return None


def _allowed_catalog_vocabulary(catalog: dict[str, Any]) -> dict[str, list[str]]:
    def labels(entries: list[dict[str, Any]], *, facility: bool = False) -> list[str]:
        result: set[str] = set()
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            values = [
                entry.get("value"),
                entry.get("canonical_name"),
                entry.get("display_name"),
                *entry.get("source_values", []),
                *entry.get("aliases", []),
            ]
            for value in values:
                if isinstance(value, str) and value.strip():
                    result.add(value.strip())
        return sorted(result)[:120]

    return {
        "faculties": labels(catalog.get("faculties", [])),
        "buildings": labels(catalog.get("buildings", [])),
        "facilities": labels(catalog.get("facilities", []), facility=True),
    }


def interpret_with_ai_fallback(
    message: str,
    catalog: dict[str, Any],
    settings: Settings,
) -> AIIntentInterpretation | None:
    """Call one configured OpenAI-compatible provider once; fail closed on any issue."""
    if not settings.assistant_ai_enabled:
        return None
    endpoint = settings.assistant_ai_endpoint_url
    model = settings.assistant_ai_model
    if not endpoint or not model:
        return None

    vocabulary = _allowed_catalog_vocabulary(catalog)
    system_prompt = (
        "You classify a single Indonesian student message for a campus room assistant. "
        "Return exactly one JSON object and no markdown. Never invent a faculty, building, "
        "or facility; choose only exact observed labels from the supplied catalogue or null. "
        "Do not claim room availability, create/cancel reservations, access personal records, "
        "or return room data. Allowed intents: ROOM_SEARCH, ROOM_AVAILABILITY, ALTERNATIVE_SLOTS. "
        "Extract only fields explicitly supported by the message. For availability or alternative "
        "slots, extract an ISO date and complete start/end times only when stated. "
        "Schema: {intent, faculty, building, min_capacity, facilities, date, start_time, "
        "end_time, participant_count}. Use null for unknown scalar fields and [] for facilities."
    )
    user_prompt = json.dumps(
        {
            "message": message[:1000],
            "observed_catalogue": vocabulary,
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    if settings.assistant_ai_api_key:
        headers["Authorization"] = f"Bearer {settings.assistant_ai_api_key}"

    try:
        response = httpx.post(
            endpoint,
            headers=headers,
            json={
                "model": model,
                "temperature": 0,
                "max_tokens": 180,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            },
            timeout=settings.assistant_ai_timeout_seconds,
            follow_redirects=False,
        )
        response.raise_for_status()
        envelope = response.json()
        raw_content = envelope["choices"][0]["message"]["content"]
        if not isinstance(raw_content, str):
            return None
        parsed = AIIntentInterpretation.model_validate(json.loads(raw_content))

        # Resolve every supplied campus value against active-room data, failing closed on unknown labels.
        if parsed.faculty is not None:
            faculty = _catalog_label(parsed.faculty, catalog.get("faculties", []))
            if faculty is None:
                return None
            parsed.faculty = faculty
        if parsed.building is not None:
            building = _catalog_label(parsed.building, catalog.get("buildings", []))
            if building is None:
                return None
            parsed.building = building
        resolved_facilities: list[str] = []
        for item in parsed.facilities:
            facility = _catalog_label(item, catalog.get("facilities", []), facility=True)
            if facility is None:
                return None
            resolved_facilities.append(facility)
        parsed.facilities = list(dict.fromkeys(resolved_facilities))

        if parsed.start_time and parsed.end_time and parsed.end_time <= parsed.start_time:
            return None
        if parsed.intent in {"ROOM_AVAILABILITY", "ALTERNATIVE_SLOTS"}:
            if not (parsed.date and parsed.start_time and parsed.end_time):
                # Let the deterministic response composer ask for the missing time fields.
                return parsed
        return parsed
    except (httpx.HTTPError, ValueError, KeyError, TypeError, IndexError):
        logger.info("Assistant AI fallback unavailable or returned invalid output")
        return None
