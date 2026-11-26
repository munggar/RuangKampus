from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from ruangkampus.database import Base
from ruangkampus.models import AssistantLearningFeedback, User
from ruangkampus.services.assistant_adaptive_learning import get_adaptive_learning_preferences


def _session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return engine, Session(engine)


def test_adaptation_requires_repeated_explicit_feedback_and_is_user_scoped():
    engine, db = _session()
    try:
        student_a = User(
            name="Student A",
            email="student-a@example.test",
            password_hash="not-a-real-password-hash",
        )
        student_b = User(
            name="Student B",
            email="student-b@example.test",
            password_hash="not-a-real-password-hash",
        )
        db.add_all([student_a, student_b])
        db.flush()
        now = datetime.now(timezone.utc)
        db.add_all([
            AssistantLearningFeedback(
                user_id=student_a.id,
                intent="SMALLTALK",
                rating="NOT_HELPFUL",
                reason_code="TOO_FORMAL",
                created_at=now - timedelta(days=1),
            ),
            AssistantLearningFeedback(
                user_id=student_a.id,
                intent="ROOM_SEARCH",
                rating="NOT_HELPFUL",
                reason_code="TOO_FORMAL",
                created_at=now,
            ),
            AssistantLearningFeedback(
                user_id=student_b.id,
                intent="SMALLTALK",
                rating="NOT_HELPFUL",
                reason_code="TOO_LONG",
                created_at=now,
            ),
        ])
        db.commit()

        preferences_a = get_adaptive_learning_preferences(db, student_a.id)
        preferences_b = get_adaptive_learning_preferences(db, student_b.id)

        assert len(preferences_a) == 1
        assert "casual" in preferences_a[0].lower()
        assert preferences_b == []
    finally:
        db.close()
        engine.dispose()


def test_old_or_helpful_feedback_does_not_change_preferences():
    engine, db = _session()
    try:
        student = User(
            name="Student",
            email="student@example.test",
            password_hash="not-a-real-password-hash",
        )
        db.add(student)
        db.flush()
        db.add_all([
            AssistantLearningFeedback(
                user_id=student.id,
                intent="SMALLTALK",
                rating="NOT_HELPFUL",
                reason_code="TOO_LONG",
                created_at=datetime.now(timezone.utc) - timedelta(days=120),
            ),
            AssistantLearningFeedback(
                user_id=student.id,
                intent="SMALLTALK",
                rating="HELPFUL",
                reason_code=None,
            ),
        ])
        db.commit()

        assert get_adaptive_learning_preferences(db, student.id) == []
    finally:
        db.close()
        engine.dispose()
