"""enforce one-time or recurring schedule discriminator

Revision ID: c3d7e91a4b02
Revises: b2c6a84f913d
Create Date: 2026-11-25 17:25:00.000000
"""
from typing import Sequence, Union

from alembic import op

revision: str = "c3d7e91a4b02"
down_revision: Union[str, None] = "b2c6a84f913d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("lecture_schedules") as batch_op:
        batch_op.drop_constraint("ck_schedules_has_date_or_weekday", type_="check")
        batch_op.create_check_constraint(
            "ck_schedules_has_date_or_weekday",
            "(schedule_date IS NOT NULL AND day_of_week IS NULL) OR "
            "(schedule_date IS NULL AND day_of_week IS NOT NULL)",
        )


def downgrade() -> None:
    with op.batch_alter_table("lecture_schedules") as batch_op:
        batch_op.drop_constraint("ck_schedules_has_date_or_weekday", type_="check")
        batch_op.create_check_constraint(
            "ck_schedules_has_date_or_weekday",
            "schedule_date IS NOT NULL OR day_of_week IS NOT NULL",
        )
