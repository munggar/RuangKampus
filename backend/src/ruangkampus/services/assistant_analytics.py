from __future__ import annotations

import logging

logger = logging.getLogger("ruangkampus.assistant.analytics")


def record_assistant_outcome(
    *,
    intent: str,
    matched_rule: str,
    confidence: float | None,
    confidence_basis: str,
    result_type: str,
    requires_clarification: bool,
    ai_fallback_used: bool,
) -> None:
    """Emit aggregate-safe structured telemetry; never include text, IDs, or reservation data."""
    logger.info(
        "assistant_analytics intent=%s rule=%s confidence=%s confidence_basis=%s "
        "result_type=%s clarification=%s ai_fallback=%s",
        intent,
        matched_rule,
        confidence if confidence is not None else "none",
        confidence_basis,
        result_type,
        str(bool(requires_clarification)).lower(),
        str(bool(ai_fallback_used)).lower(),
    )
