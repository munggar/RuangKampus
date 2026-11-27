from __future__ import annotations

from datetime import time
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ruangkampus.models import Room


# Preserve the exact vocabulary already used by the original room-assistant parser.
# These aliases are code-supported; no additional synonym is inferred from room data.
FACILITY_TERMS: dict[str, tuple[str, ...]] = {
    "projector": ("projector", "proyektor"),
    "whiteboard": ("whiteboard", "papan tulis"),
    "wifi": ("wifi", "wi-fi", "internet"),
    "air conditioner": ("ac", "air conditioner", "pendingin"),
    "sound system": ("sound system", "speaker", "audio"),
    "computer": ("komputer", "computer", "pc"),
}

PLACEHOLDER_VALUES = frozenset({
    "-", "n/a", "na", "none", "null", "unknown", "tidak diketahui",
    "belum ditentukan", "belum tersedia", "belum diisi",
})
WEEKDAY_KEYS = frozenset({
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
})


def normalize_catalog_label(value: str) -> str:
    """Normalize whitespace and casing for comparisons without changing source data."""
    return " ".join(value.split()).casefold()


def is_usable_catalog_label(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    normalized = normalize_catalog_label(value)
    return bool(normalized) and normalized not in PLACEHOLDER_VALUES


def _load_active_rooms(db: Session) -> list[Room]:
    return db.scalars(
        select(Room)
        .where(Room.deleted_at.is_(None), Room.room_status == "ACTIVE")
        .order_by(Room.room_name.asc(), Room.id.asc())
    ).all()


def _display_value(source_values: set[str]) -> str:
    return min((value.strip() for value in source_values), key=lambda item: (item.casefold(), item))


def _group_room_labels(rooms: list[Room], attribute: str) -> list[dict[str, Any]]:
    groups: dict[str, dict[str, Any]] = {}
    for room in rooms:
        raw_value = getattr(room, attribute)
        if not is_usable_catalog_label(raw_value):
            continue
        normalized = normalize_catalog_label(raw_value)
        group = groups.setdefault(normalized, {"source_values": set(), "room_ids": set()})
        group["source_values"].add(raw_value)
        group["room_ids"].add(str(room.id))

    result = []
    for group in groups.values():
        source_values = sorted(group["source_values"], key=lambda item: (item.casefold(), item))
        result.append({
            "value": _display_value(group["source_values"]),
            "source_values": source_values,
            "room_count": len(group["room_ids"]),
            "has_spelling_variants": len(source_values) > 1,
        })
    return sorted(result, key=lambda item: (item["value"].casefold(), item["value"]))


def _canonical_facility(value: str) -> str | None:
    normalized = normalize_catalog_label(value)
    for canonical, aliases in FACILITY_TERMS.items():
        if normalized in {normalize_catalog_label(alias) for alias in aliases}:
            return canonical
    return None


def _facility_catalog(rooms: list[Room]) -> list[dict[str, Any]]:
    groups: dict[str, dict[str, Any]] = {}
    for room in rooms:
        raw_facilities = room.facilities
        if not isinstance(raw_facilities, list):
            continue
        for raw_value in raw_facilities:
            if not is_usable_catalog_label(raw_value):
                continue
            canonical = _canonical_facility(raw_value)
            normalized = normalize_catalog_label(raw_value)
            key = f"known:{canonical}" if canonical else f"raw:{normalized}"
            group = groups.setdefault(
                key,
                {
                    "canonical_name": canonical,
                    "source_values": set(),
                    "room_ids": set(),
                },
            )
            group["source_values"].add(raw_value)
            group["room_ids"].add(str(room.id))

    result = []
    for group in groups.values():
        canonical = group["canonical_name"]
        source_values = sorted(group["source_values"], key=lambda item: (item.casefold(), item))
        aliases = list(FACILITY_TERMS[canonical]) if canonical else []
        result.append({
            "canonical_name": canonical,
            "display_name": canonical or _display_value(group["source_values"]),
            "source_values": source_values,
            "aliases": aliases,
            "mapping_status": "KNOWN_ALIAS_GROUP" if canonical else "UNMAPPED_SOURCE_VALUE",
            "room_count": len(group["room_ids"]),
        })
    return sorted(result, key=lambda item: (item["display_name"].casefold(), item["display_name"]))


def find_facility_matches(catalog: dict[str, Any], query: str) -> list[dict[str, Any]]:
    """Find observed facilities by exact/partial label or an existing code-supported alias.

    Unknown source values are searchable by their own observed text only; they are never
    assigned to a known canonical facility.
    """
    normalized_query = normalize_catalog_label(query)
    if not normalized_query:
        return []

    matches = []
    for entry in catalog.get("facilities", []):
        candidates = [entry["display_name"], *entry.get("source_values", [])]
        if entry.get("canonical_name"):
            candidates.extend(entry.get("aliases", []))
        normalized_candidates = [normalize_catalog_label(value) for value in candidates]
        if any(
            normalized_query == candidate
            or normalized_query in candidate
            or candidate in normalized_query
            for candidate in normalized_candidates
            if candidate
        ):
            matches.append(entry)
    return matches


def _operating_hours_state(value: Any) -> tuple[str, list[str]]:
    if value is None or value == {}:
        return "MISSING", ["OPERATING_HOURS_MISSING"]
    if not isinstance(value, dict):
        return "INCONSISTENT", ["OPERATING_HOURS_NOT_AN_OBJECT"]

    issues: list[str] = []
    valid_window_count = 0
    for day, windows in value.items():
        day_key = str(day).casefold()
        if day_key not in WEEKDAY_KEYS:
            issues.append("UNKNOWN_OPERATING_DAY")
            continue
        if not isinstance(windows, list) or not windows:
            issues.append("EMPTY_OR_INVALID_OPERATING_WINDOWS")
            continue

        parsed_windows: list[tuple[time, time]] = []
        for window in windows:
            if not isinstance(window, dict):
                issues.append("INVALID_OPERATING_WINDOW")
                continue
            try:
                start_value = window.get("start")
                end_value = window.get("end")
                start = start_value if isinstance(start_value, time) else time.fromisoformat(str(start_value))
                end = end_value if isinstance(end_value, time) else time.fromisoformat(str(end_value))
            except (TypeError, ValueError):
                issues.append("INVALID_OPERATING_WINDOW")
                continue
            if start.tzinfo is not None or end.tzinfo is not None:
                issues.append("TIMEZONE_AWARE_OPERATING_WINDOW")
                continue
            if end <= start:
                issues.append("INVALID_OPERATING_WINDOW_RANGE")
                continue
            parsed_windows.append((start, end))
            valid_window_count += 1

        parsed_windows.sort()
        if any(current[0] < previous[1] for previous, current in zip(parsed_windows, parsed_windows[1:])):
            issues.append("OVERLAPPING_OPERATING_WINDOWS")

    if issues:
        return "INCONSISTENT", sorted(set(issues))
    if valid_window_count == 0:
        return "MISSING", ["OPERATING_HOURS_MISSING"]
    return "VALID", []


def _room_quality(room: Room) -> dict[str, Any]:
    issues: list[str] = []
    inconsistent = False
    incomplete = False

    for attribute, issue_code in (
        ("faculty", "FACULTY_MISSING_OR_PLACEHOLDER"),
        ("building", "BUILDING_MISSING_OR_PLACEHOLDER"),
    ):
        if not is_usable_catalog_label(getattr(room, attribute)):
            incomplete = True
            issues.append(issue_code)

    if not is_usable_catalog_label(room.location_description):
        incomplete = True
        issues.append("LOCATION_DESCRIPTION_MISSING_OR_PLACEHOLDER")

    if not is_usable_catalog_label(room.room_name) or not isinstance(room.capacity, int) or room.capacity <= 0:
        inconsistent = True
        issues.append("INVALID_REQUIRED_ROOM_METADATA")

    if not isinstance(room.facilities, list):
        inconsistent = True
        issues.append("FACILITIES_NOT_A_LIST")
    else:
        usable_facilities = [
            value for value in room.facilities if is_usable_catalog_label(value)
        ]
        if not usable_facilities:
            incomplete = True
            issues.append("FACILITIES_MISSING")
        if any(not isinstance(value, str) for value in room.facilities):
            inconsistent = True
            issues.append("FACILITY_VALUE_NOT_A_STRING")
        normalized_values = [normalize_catalog_label(value) for value in usable_facilities]
        if len(normalized_values) != len(set(normalized_values)):
            inconsistent = True
            issues.append("DUPLICATE_FACILITY_LABELS")

    hours_state, hours_issues = _operating_hours_state(room.operating_hours)
    if hours_state == "MISSING":
        incomplete = True
    elif hours_state == "INCONSISTENT":
        inconsistent = True
    issues.extend(hours_issues)

    status = "INCONSISTENT" if inconsistent else "INCOMPLETE" if incomplete else "VALID"
    return {
        "room_id": str(room.id),
        "room_name": room.room_name,
        "status": status,
        "operating_hours_status": hours_state,
        "issues": sorted(set(issues)),
    }


def _variation_groups(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "value": entry["value"],
            "source_values": entry["source_values"],
            "room_count": entry["room_count"],
        }
        for entry in entries
        if entry.get("has_spelling_variants")
    ]


def _quality_report(rooms: list[Room]) -> dict[str, Any]:
    faculty = _group_room_labels(rooms, "faculty")
    buildings = _group_room_labels(rooms, "building")
    facilities = _facility_catalog(rooms)

    faculty_populated = sum(is_usable_catalog_label(room.faculty) for room in rooms)
    faculty_placeholder = sum(
        isinstance(room.faculty, str)
        and normalize_catalog_label(room.faculty) in PLACEHOLDER_VALUES
        for room in rooms
    )
    building_populated = sum(is_usable_catalog_label(room.building) for room in rooms)
    building_placeholder = sum(
        isinstance(room.building, str)
        and normalize_catalog_label(room.building) in PLACEHOLDER_VALUES
        for room in rooms
    )
    location_populated = sum(is_usable_catalog_label(room.location_description) for room in rooms)

    facility_populated = 0
    facility_placeholder_values = 0
    for room in rooms:
        values = room.facilities if isinstance(room.facilities, list) else []
        valid_values = [value for value in values if is_usable_catalog_label(value)]
        facility_populated += bool(valid_values)
        facility_placeholder_values += sum(
            isinstance(value, str) and normalize_catalog_label(value) in PLACEHOLDER_VALUES
            for value in values
        )

    assessments = [_room_quality(room) for room in rooms]
    quality_counts = {state: 0 for state in ("VALID", "INCOMPLETE", "INCONSISTENT", "UNVERIFIABLE")}
    for assessment in assessments:
        quality_counts[assessment["status"]] += 1

    hours_counts = {
        "valid": sum(item["operating_hours_status"] == "VALID" for item in assessments),
        "missing": sum(item["operating_hours_status"] == "MISSING" for item in assessments),
        "inconsistent": sum(item["operating_hours_status"] == "INCONSISTENT" for item in assessments),
    }
    unmapped = [
        {"value": value, "room_count": entry["room_count"]}
        for entry in facilities
        if entry["canonical_name"] is None
        for value in entry["source_values"]
    ]

    return {
        "verification_status": "VERIFIED",
        "source": "rooms",
        "scope": "non-deleted rooms with room_status=ACTIVE",
        "active_room_count": len(rooms),
        "room_quality_counts": quality_counts,
        "fields": {
            "faculty": {
                "populated_rooms": faculty_populated,
                "missing_or_placeholder_rooms": len(rooms) - faculty_populated,
                "placeholder_rooms": faculty_placeholder,
                "distinct_values": faculty,
                "spelling_variation_groups": _variation_groups(faculty),
            },
            "building": {
                "populated_rooms": building_populated,
                "missing_or_placeholder_rooms": len(rooms) - building_populated,
                "placeholder_rooms": building_placeholder,
                "distinct_values": buildings,
                "spelling_variation_groups": _variation_groups(buildings),
            },
            "facilities": {
                "populated_rooms": facility_populated,
                "missing_or_placeholder_rooms": len(rooms) - facility_populated,
                "placeholder_values": facility_placeholder_values,
                "distinct_values": facilities,
                "observed_variant_groups": [
                    {
                        "canonical_name": entry["canonical_name"],
                        "display_name": entry["display_name"],
                        "source_values": entry["source_values"],
                        "room_count": entry["room_count"],
                    }
                    for entry in facilities
                    if len(entry["source_values"]) > 1
                ],
                "unmapped_source_values": unmapped,
            },
            "location_description": {
                "populated_rooms": location_populated,
                "missing_or_placeholder_rooms": len(rooms) - location_populated,
            },
            "operating_hours": hours_counts,
        },
        "room_assessments": assessments,
    }


def build_assistant_data_catalog(db: Session) -> dict[str, Any]:
    """Build an in-memory catalogue from active, non-deleted room records; never writes data."""
    rooms = _load_active_rooms(db)
    return {
        "verification_status": "VERIFIED",
        "source": "rooms",
        "scope": "non-deleted rooms with room_status=ACTIVE",
        "faculties": _group_room_labels(rooms, "faculty"),
        "facilities": _facility_catalog(rooms),
        "buildings": _group_room_labels(rooms, "building"),
        "rooms": [
            {
                "id": str(room.id),
                "room_name": room.room_name,
                "room_code": room.room_code,
                "faculty": room.faculty,
                "building": room.building,
                "floor": room.floor,
                "location_description": room.location_description,
                "capacity": room.capacity,
                "facilities": room.facilities,
                "operating_hours": room.operating_hours,
            }
            for room in rooms
        ],
        "data_quality": _quality_report(rooms),
    }


def assess_assistant_data_quality(db: Session) -> dict[str, Any]:
    """Return a read-only quality report and distinguish database query failure from empty data."""
    try:
        rooms = _load_active_rooms(db)
    except SQLAlchemyError as exc:
        return {
            "verification_status": "UNABLE_TO_VERIFY",
            "source": "rooms",
            "scope": "non-deleted rooms with room_status=ACTIVE",
            "reason_code": "DATABASE_QUERY_FAILED",
            "exception_type": type(exc).__name__,
            "active_room_count": None,
            "room_quality_counts": {
                "VALID": None,
                "INCOMPLETE": None,
                "INCONSISTENT": None,
                "UNVERIFIABLE": None,
            },
        }
    return _quality_report(rooms)
