"""add schedule import batches and notification idempotency

Revision ID: b2c6a84f913d
Revises: 6720eddb3245
Create Date: 2026-11-25 17:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "b2c6a84f913d"
down_revision: Union[str, None] = "6720eddb3245"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("notifications", sa.Column("email_attempted_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "notifications",
        sa.Column("email_attempt_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
    )
    op.add_column("notifications", sa.Column("event_key", sa.String(length=180), nullable=True))
    op.create_index("uq_notifications_event_key", "notifications", ["event_key"], unique=True)

    op.create_table(
        "schedule_import_batches",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_by_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="PREVIEWED"),
        sa.Column("source_filename", sa.String(length=255), nullable=False),
        sa.Column("file_sha256", sa.String(length=64), nullable=False),
        sa.Column("row_count", sa.Integer(), nullable=False),
        sa.Column("valid_count", sa.Integer(), nullable=False),
        sa.Column("invalid_count", sa.Integer(), nullable=False),
        sa.Column("parsed_rows", sa.JSON(), nullable=False),
        sa.Column("row_results", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status IN ('PREVIEWED', 'COMPLETED', 'FAILED')", name="ck_schedule_import_status"),
        sa.CheckConstraint("row_count >= 0 AND valid_count >= 0 AND invalid_count >= 0", name="ck_schedule_import_counts"),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_schedule_import_creator_created", "schedule_import_batches", ["created_by_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_schedule_import_creator_created", table_name="schedule_import_batches")
    op.drop_table("schedule_import_batches")
    op.drop_index("uq_notifications_event_key", table_name="notifications")
    op.drop_column("notifications", "event_key")
    op.drop_column("notifications", "email_attempt_count")
    op.drop_column("notifications", "email_attempted_at")
