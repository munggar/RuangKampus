import logging
from types import SimpleNamespace

from ruangkampus.services.assistant_analytics import record_assistant_outcome
from ruangkampus.services.assistant_confidence import evaluate_rule_confidence
from ruangkampus.services.assistant_function_registry import get_assistant_function, registered_intents


def test_rule_confidence_is_deterministic_and_not_zero_for_matched_rule():
    detection = SimpleNamespace(
        matched_rule="ROOM_SEARCH_VERB",
        intent="ROOM_SEARCH",
        requires_clarification=False,
    )
    assert evaluate_rule_confidence(detection) == 0.97


def test_clarification_reduces_rule_strength_without_claiming_probability():
    detection = SimpleNamespace(
        matched_rule="ROOM_REFERENCE_NEEDS_CRITERIA",
        intent="ROOM_SEARCH",
        requires_clarification=True,
    )
    assert evaluate_rule_confidence(detection) == 0.8


def test_function_registry_is_allowlisted_and_preview_actions_are_not_mutations():
    assert get_assistant_function("ROOM_SEARCH").function_name == "search_rooms"
    assert get_assistant_function("MY_RESERVATIONS").owner_scoped is True
    assert get_assistant_function("RESERVATION_CREATE_PREVIEW").access == "PREVIEW"
    assert get_assistant_function("RESERVATION_CREATE_PREVIEW").confirmation_required is True
    assert get_assistant_function("DROP_TABLE") is None
    assert "OUT_OF_SCOPE" in registered_intents()


def test_analytics_excludes_raw_messages_and_user_identifiers(caplog):
    caplog.set_level(logging.INFO, logger="ruangkampus.assistant.analytics")
    record_assistant_outcome(
        intent="ROOM_SEARCH",
        matched_rule="ROOM_SEARCH_VERB",
        confidence=0.97,
        confidence_basis="RULE_HEURISTIC",
        result_type="ROOMS_FOUND",
        requires_clarification=False,
        ai_fallback_used=False,
    )
    message = caplog.records[-1].getMessage()
    assert "ROOM_SEARCH" in message
    assert "raw_text" not in message
    assert "user_id" not in message
    assert "2403045007" not in message
