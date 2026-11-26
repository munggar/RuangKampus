from __future__ import annotations

from typing import Any

# Rule-strength values are deterministic heuristics, not calibrated probabilities.
_RULE_STRENGTH: dict[str, float] = {
    "EMPTY_INPUT": 0.99,
    "ROOM_SEARCH_VERB": 0.97,
    "STRUCTURED_ROOM_FILTERS": 0.96,
    "STRUCTURED_AVAILABILITY_FILTERS": 0.98,
    "ROOM_AVAILABILITY_REQUEST": 0.96,
    "ALTERNATIVE_SLOT_REQUEST": 0.98,
    "ROOM_DETAIL_QUESTION": 0.95,
    "RESERVATION_HELP_QUESTION": 0.98,
    "MY_RESERVATION_LIST": 0.97,
    "RESERVATION_STATUS_QUERY": 0.97,
    "RESERVATION_CANCEL_REQUEST": 0.96,
    "RESERVATION_CREATE_REQUEST": 0.96,
    "RUANGKAMPUS_FAQ": 0.96,
    "SMALLTALK_GREETING": 0.99,
    "SMALLTALK_THANKS": 0.99,
    "SMALLTALK_CASUAL": 0.91,
    "ROOM_REFERENCE_NEEDS_CRITERIA": 0.84,
    "NO_SUPPORTED_INTENT": 0.60,
    "AI_INTENT_FALLBACK": 0.62,
}


def evaluate_rule_confidence(
    detection: Any,
    *,
    has_catalog_match: bool = False,
    has_complete_availability_window: bool = False,
) -> float:
    """Return a deterministic rule-strength score, not a model likelihood."""
    score = _RULE_STRENGTH.get(detection.matched_rule, 0.70)
    if has_catalog_match and detection.intent in {"ROOM_SEARCH", "ROOM_AVAILABILITY", "ROOM_DETAIL"}:
        score = min(0.995, score + 0.02)
    if has_complete_availability_window and detection.intent in {"ROOM_AVAILABILITY", "ALTERNATIVE_SLOTS"}:
        score = min(0.995, score + 0.015)
    if detection.requires_clarification:
        score = max(0.50, score - 0.04)
    return round(score, 3)
