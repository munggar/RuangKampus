"""initial core schema

Revision ID: 6720eddb3245
Revises:
Create Date: 2026-11-25 09:14:32.931931
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "6720eddb3245"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "rooms",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("room_name", sa.String(length=160), nullable=False),
        sa.Column("room_code", sa.String(length=80), nullable=True),
        sa.Column("building", sa.String(length=160), nullable=False),
        sa.Column("floor", sa.String(length=40), nullable=True),
        sa.Column("capacity", sa.Integer(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("facilities", sa.JSON(), nullable=False),
        sa.Column("operating_hours", sa.JSON(), nullable=False),
        sa.Column("room_status", sa.String(length=20), nullable=False),
        sa.Column("photo_url", sa.String(length=2048), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("room_status IN ('ACTIVE', 'INACTIVE', 'MAINTENANCE')", name="ck_rooms_status"),
        sa.CheckConstraint("capacity > 0", name="ck_rooms_capacity_positive"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("room_code"),
    )
    op.create_index("ix_rooms_building_status", "rooms", ["building", "room_status", "deleted_at"])
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("student_identifier", sa.String(length=50), nullable=True),
        sa.Column("phone", sa.String(length=40), nullable=True),
        sa.Column("profile_image_url", sa.String(length=2048), nullable=True),
        sa.Column("password_hash", sa.String(length=512), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("account_status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("account_status IN ('ACTIVE', 'DISABLED')", name="ck_users_account_status"),
        sa.CheckConstraint("role IN ('STUDENT', 'TU_ADMIN')", name="ck_users_role"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("student_identifier"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_table(
        "auth_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("refresh_token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_agent", sa.String(length=512), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("refresh_token_hash"),
    )
    op.create_index("ix_auth_sessions_user_active", "auth_sessions", ["user_id", "revoked_at", "expires_at"])
    op.create_table(
        "lecture_schedules",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("room_id", sa.Uuid(), nullable=False),
        sa.Column("course_name", sa.String(length=200), nullable=False),
        sa.Column("schedule_date", sa.Date(), nullable=True),
        sa.Column("day_of_week", sa.Integer(), nullable=True),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        sa.Column("schedule_status", sa.String(length=20), nullable=False),
        sa.Column("data_source", sa.String(length=240), nullable=False),
        sa.Column("last_updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("schedule_status IN ('ACTIVE', 'CANCELLED')", name="ck_schedules_status"),
        sa.CheckConstraint("day_of_week IS NULL OR (day_of_week >= 0 AND day_of_week <= 6)", name="ck_schedules_weekday_range"),
        sa.CheckConstraint("end_time > start_time", name="ck_schedules_time_order"),
        sa.CheckConstraint("schedule_date IS NOT NULL OR day_of_week IS NOT NULL", name="ck_schedules_has_date_or_weekday"),
        sa.ForeignKeyConstraint(["room_id"], ["rooms.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_schedules_room_date", "lecture_schedules", ["room_id", "schedule_date", "day_of_week", "schedule_status"])
    op.create_table(
        "notifications",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("recipient_id", sa.Uuid(), nullable=False),
        sa.Column("notification_type", sa.String(length=60), nullable=False),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivery_status", sa.String(length=40), nullable=False),
        sa.Column("email_delivery_status", sa.String(length=40), nullable=False),
        sa.Column("email_sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["recipient_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notifications_recipient_read_created", "notifications", ["recipient_id", "read_at", "created_at"])
    op.create_table(
        "password_reset_tokens",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index("ix_password_reset_user_expiry", "password_reset_tokens", ["user_id", "expires_at"])
    op.create_table(
        "reservations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("room_id", sa.Uuid(), nullable=False),
        sa.Column("purpose", sa.String(length=240), nullable=False),
        sa.Column("reservation_date", sa.Date(), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        sa.Column("participant_count", sa.Integer(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("admin_id", sa.Uuid(), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancellation_reason", sa.Text(), nullable=True),
        sa.Column("cancelled_by_id", sa.Uuid(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("status IN ('PENDING', 'APPROVED', 'REJECTED', 'CANCELLED', 'COMPLETED')", name="ck_reservations_status"),
        sa.CheckConstraint("end_time > start_time", name="ck_reservations_time_order"),
        sa.CheckConstraint("participant_count > 0", name="ck_reservations_participants_positive"),
        sa.ForeignKeyConstraint(["admin_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["cancelled_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["room_id"], ["rooms.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_reservations_room_date_status", "reservations", ["room_id", "reservation_date", "status"])
    op.create_index("ix_reservations_user_date", "reservations", ["user_id", "reservation_date"])
    op.create_table(
        "room_unavailability",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("room_id", sa.Uuid(), nullable=False),
        sa.Column("unavailable_date", sa.Date(), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        sa.Column("reason", sa.String(length=240), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_by_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("end_time > start_time", name="ck_unavailability_time_order"),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["room_id"], ["rooms.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_unavailability_room_date", "room_unavailability", ["room_id", "unavailable_date", "is_active"])
    op.create_table(
        "room_update_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("admin_id", sa.Uuid(), nullable=False),
        sa.Column("entity_type", sa.String(length=40), nullable=False),
        sa.Column("entity_id", sa.Uuid(), nullable=False),
        sa.Column("action", sa.String(length=40), nullable=False),
        sa.Column("previous_value", sa.JSON(), nullable=True),
        sa.Column("new_value", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["admin_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_room_logs_entity_created", "room_update_logs", ["entity_type", "entity_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_room_logs_entity_created", table_name="room_update_logs")
    op.drop_table("room_update_logs")
    op.drop_index("ix_unavailability_room_date", table_name="room_unavailability")
    op.drop_table("room_unavailability")
    op.drop_index("ix_reservations_user_date", table_name="reservations")
    op.drop_index("ix_reservations_room_date_status", table_name="reservations")
    op.drop_table("reservations")
    op.drop_index("ix_password_reset_user_expiry", table_name="password_reset_tokens")
    op.drop_table("password_reset_tokens")
    op.drop_index("ix_notifications_recipient_read_created", table_name="notifications")
    op.drop_table("notifications")
    op.drop_index("ix_schedules_room_date", table_name="lecture_schedules")
    op.drop_table("lecture_schedules")
    op.drop_index("ix_auth_sessions_user_active", table_name="auth_sessions")
    op.drop_table("auth_sessions")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
    op.drop_index("ix_rooms_building_status", table_name="rooms")
    op.drop_table("rooms")
