"""add faculty and precise room location metadata

Revision ID: d4e8b71c2f90
Revises: c3d7e91a4b02
Create Date: 2026-11-25 12:30:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "d4e8b71c2f90"
down_revision: Union[str, None] = "c3d7e91a4b02"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("rooms", sa.Column("faculty", sa.String(length=160), nullable=True))
    op.add_column("rooms", sa.Column("location_description", sa.String(length=500), nullable=True))
    op.create_index(
        "ix_rooms_faculty_building_status",
        "rooms",
        ["faculty", "building", "room_status", "deleted_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_rooms_faculty_building_status", table_name="rooms")
    op.drop_column("rooms", "location_description")
    op.drop_column("rooms", "faculty")
