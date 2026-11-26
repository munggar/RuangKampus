from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ruangkampus.models import AssistantLearningFeedback

LEARNING_WINDOW_DAYS = 90
MIN_SIGNALS_FOR_ADAPTATION = 2

_ADAPTIVE_PREFERENCES = {
    "TOO_FORMAL": "Use a casual, friendly Indonesian tone instead of stiff or overly formal phrasing.",
    "TOO_LONG": "Keep answers concise and prioritize the single most useful next step.",
    "TOO_SHORT": "Give enough context and a practical explanation so the answer is actionable.",
    "WRONG_INTENT": "When the user's intent is ambiguous, briefly confirm your understanding or ask one clarifying question instead of guessing.",
    "WRONG_NORMALIZATION": "Treat ambiguous and regional slang conservatively; preserve uncertain wording and ask for context rather than guessing its meaning.",
    "RESULTS_NOT_RELEVANT": "Never relax a user's explicit room, facility, capacity, faculty, date, or time constraints; say clearly when verified data has no match.",
}


def get_adaptive_learning_preferences(db: Session, user_id: UUID) -> list[str]:
    """Apply only repeated, explicit feedback from this student in the last 90 days.

    Feedback contains allowlisted reason codes only: no chat messages, tokens, room
    records, reservations, or provider output are retained or used as learning input.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=LEARNING_WINDOW_DAYS)
    statement = (
        select(
            AssistantLearningFeedback.reason_code,
            func.count(AssistantLearningFeedback.id).label("signal_count"),
        )
        .where(
            AssistantLearningFeedback.user_id == user_id,
            AssistantLearningFeedback.rating == "NOT_HELPFUL",
            AssistantLearningFeedback.created_at >= cutoff,
            AssistantLearningFeedback.reason_code.in_(tuple(_ADAPTIVE_PREFERENCES)),
        )
        .group_by(AssistantLearningFeedback.reason_code)
        .having(func.count(AssistantLearningFeedback.id) >= MIN_SIGNALS_FOR_ADAPTATION)
        .order_by(func.count(AssistantLearningFeedback.id).desc())
        .limit(5)
    )
    rows = db.execute(statement).all()
    return [
        _ADAPTIVE_PREFERENCES[reason_code]
        for reason_code, _count in rows
        if reason_code in _ADAPTIVE_PREFERENCES
    ]
