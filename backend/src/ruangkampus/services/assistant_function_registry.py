from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class AssistantFunctionSpec:
    intent: str
    function_name: str
    access: Literal["READ_ONLY", "PREVIEW"]
    owner_scoped: bool = False
    confirmation_required: bool = False


# Strict allowlist: model output can select an intent, never a Python function or SQL query.
_FUNCTIONS: dict[str, AssistantFunctionSpec] = {
    "ROOM_SEARCH": AssistantFunctionSpec("ROOM_SEARCH", "search_rooms", "READ_ONLY"),
    "ROOM_AVAILABILITY": AssistantFunctionSpec("ROOM_AVAILABILITY", "check_room_availability", "READ_ONLY"),
    "ALTERNATIVE_SLOTS": AssistantFunctionSpec("ALTERNATIVE_SLOTS", "find_alternative_slots", "READ_ONLY"),
    "ROOM_DETAIL": AssistantFunctionSpec("ROOM_DETAIL", "get_room_detail", "READ_ONLY"),
    "MY_RESERVATIONS": AssistantFunctionSpec("MY_RESERVATIONS", "list_my_reservations", "READ_ONLY", owner_scoped=True),
    "RESERVATION_STATUS": AssistantFunctionSpec("RESERVATION_STATUS", "get_my_reservation_status", "READ_ONLY", owner_scoped=True),
    "RESERVATION_HELP": AssistantFunctionSpec("RESERVATION_HELP", "explain_reservation_workflow", "READ_ONLY"),
    "RESERVATION_CREATE_PREVIEW": AssistantFunctionSpec("RESERVATION_CREATE_PREVIEW", "preview_reservation_request", "PREVIEW", owner_scoped=True, confirmation_required=True),
    "RESERVATION_CANCEL_PREVIEW": AssistantFunctionSpec("RESERVATION_CANCEL_PREVIEW", "preview_reservation_cancellation", "PREVIEW", owner_scoped=True, confirmation_required=True),
    "FAQ": AssistantFunctionSpec("FAQ", "answer_ruangkampus_faq", "READ_ONLY"),
    "SMALLTALK": AssistantFunctionSpec("SMALLTALK", "smalltalk_response", "READ_ONLY"),
    "OUT_OF_SCOPE": AssistantFunctionSpec("OUT_OF_SCOPE", "out_of_scope_response", "READ_ONLY"),
}


def get_assistant_function(intent: str) -> AssistantFunctionSpec | None:
    """Resolve an intent to a fixed capability; unknown names never dispatch."""
    return _FUNCTIONS.get(intent)


def registered_intents() -> frozenset[str]:
    return frozenset(_FUNCTIONS)
