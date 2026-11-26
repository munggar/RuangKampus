"""add room import batches and estimated capacity

Revision ID: e5f9c82a1d43
Revises: d4e8b71c2f90
Create Date: 2026-11-26 13:10:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "e5f9c82a1d43"
down_revision: Union[str, None] = "d4e8b71c2f90"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("rooms", sa.Column("capacity_estimate", sa.String(length=40), nullable=True))
    op.create_table(
        "room_import_batches",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_by_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("source_filename", sa.String(length=255), nullable=False),
        sa.Column("file_sha256", sa.String(length=64), nullable=False),
        sa.Column("row_count", sa.Integer(), nullable=False),
        sa.Column("valid_count", sa.Integer(), nullable=False),
        sa.Column("invalid_count", sa.Integer(), nullable=False),
        sa.Column("parsed_rows", sa.JSON(), nullable=False),
        sa.Column("row_results", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status IN ('PREVIEWED', 'COMPLETED', 'FAILED')", name="ck_room_import_status"),
        sa.CheckConstraint("row_count >= 0 AND valid_count >= 0 AND invalid_count >= 0", name="ck_room_import_counts"),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_room_import_creator_created", "room_import_batches", ["created_by_id", "created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_room_import_creator_created", table_name="room_import_batches")
    op.drop_table("room_import_batches")
    op.drop_column("rooms", "capacity_estimate")
