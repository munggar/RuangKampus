"""add action targets to notification records

Revision ID: a9d4c7e2b613
Revises: f7c2a91d6e40
Create Date: 2026-11-26 23:10:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "a9d4c7e2b613"
down_revision: Union[str, None] = "f7c2a91d6e40"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("notifications", sa.Column("action_url", sa.String(length=500), nullable=True))


def downgrade() -> None:
    op.drop_column("notifications", "action_url")
