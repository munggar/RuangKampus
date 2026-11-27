"""add privacy-preserving assistant learning feedback signals

Revision ID: a81d0e4b7c92
Revises: f7c2a91d6e40
Create Date: 2026-11-26 22:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "a81d0e4b7c92"
down_revision: Union[str, None] = "f7c2a91d6e40"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.create_table(
        "assistant_learning_feedback",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("intent", sa.String(length=40), nullable=False),
        sa.Column("rating", sa.String(length=20), nullable=False),
        sa.Column("reason_code", sa.String(length=40), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "rating IN ('HELPFUL', 'NOT_HELPFUL')",
            name="ck_assistant_learning_feedback_rating",
        ),
        sa.CheckConstraint(
            "reason_code IS NULL OR reason_code IN "
            "('TOO_FORMAL', 'TOO_LONG', 'TOO_SHORT', 'WRONG_INTENT', "
            "'WRONG_NORMALIZATION', 'RESULTS_NOT_RELEVANT', 'OTHER')",
            name="ck_assistant_learning_feedback_reason",
        ),
        sa.CheckConstraint(
            "(rating = 'HELPFUL' AND reason_code IS NULL) OR "
            "(rating = 'NOT_HELPFUL' AND reason_code IS NOT NULL)",
            name="ck_assistant_learning_feedback_rating_reason",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_assistant_learning_feedback_user_created",
        "assistant_learning_feedback",
        ["user_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_assistant_learning_feedback_user_created",
        table_name="assistant_learning_feedback",
    )
    op.drop_table("assistant_learning_feedback")
