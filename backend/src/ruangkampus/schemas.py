from datetime import date, datetime, time
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, HttpUrl, field_validator, model_validator


class Role(str, Enum):
    STUDENT = "STUDENT"
    TU_ADMIN = "TU_ADMIN"


class ReservationStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"
    COMPLETED = "COMPLETED"


class BaseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class RegisterIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=2, max_length=160)
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)
    phone: str | None = Field(default=None, max_length=40)
    student_identifier: str | None = Field(default=None, min_length=3, max_length=50)


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserOut(BaseOut):
    id: UUID
    name: str
    email: EmailStr
    student_identifier: str | None
    phone: str | None
    profile_image_url: str | None
    # Public API labels match the existing frontend AuthContext contract.
    # Database/authorization values remain STUDENT and TU_ADMIN internally.
    role: str
    account_status: str
    created_at: datetime

    @field_validator("role", mode="before")
    @classmethod
    def map_internal_role_to_client_label(cls, value):
        mapping = {"STUDENT": "Student", "TU_ADMIN": "TU/Admin"}
        if value in mapping:
            return mapping[value]
        if value in mapping.values():
            return value
        raise ValueError("Unsupported account role")


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserOut


class ProfileUpdateIn(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=160)
    phone: str | None = Field(default=None, max_length=40)
    profile_image_url: HttpUrl | None = None

    @model_validator(mode="after")
    def name_cannot_be_null(self):
        if "name" in self.model_fields_set and self.name is None:
            raise ValueError("name cannot be null")
        return self


class PasswordChangeIn(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=10, max_length=128)


class ForgotPasswordIn(BaseModel):
    email: EmailStr


class ResetPasswordIn(BaseModel):
    token: str = Field(min_length=32, max_length=256)
    new_password: str = Field(min_length=10, max_length=128)


class UserStatusUpdateIn(BaseModel):
    account_status: str = Field(pattern="^(ACTIVE|DISABLED)$")


class UserRoleUpdateIn(BaseModel):
    role: Role


class OperatingWindow(BaseModel):
    start: time
    end: time

    @model_validator(mode="after")
    def validate_window(self):
        if self.end <= self.start:
            raise ValueError("Operating-hour end must be later than start")
        return self


class RoomCreateIn(BaseModel):
    room_name: str = Field(min_length=2, max_length=160)
    room_code: str | None = Field(default=None, max_length=80)
    building: str = Field(min_length=1, max_length=160)
    floor: str | None = Field(default=None, max_length=40)
    capacity: int = Field(gt=0, le=10000)
    description: str | None = Field(default=None, max_length=5000)
    facilities: list[str] = Field(default_factory=list, max_length=100)
    operating_hours: dict[str, list[OperatingWindow]] = Field(default_factory=dict)
    room_status: str = Field(default="ACTIVE", pattern="^(ACTIVE|INACTIVE|MAINTENANCE)$")
    photo_url: HttpUrl | None = None

    @field_validator("facilities")
    @classmethod
    def clean_facilities(cls, values):
        cleaned = list(dict.fromkeys(item.strip() for item in values if item.strip()))
        if len(cleaned) > 100:
            raise ValueError("At most 100 facilities are allowed")
        return cleaned

    @field_validator("operating_hours")
    @classmethod
    def validate_days(cls, value):
        allowed = {"monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"}
        unknown = set(value) - allowed
        if unknown:
            raise ValueError(f"Unsupported operating-hours day keys: {', '.join(sorted(unknown))}")
        return value


class RoomUpdateIn(BaseModel):
    room_name: str | None = Field(default=None, min_length=2, max_length=160)
    room_code: str | None = Field(default=None, max_length=80)
    building: str | None = Field(default=None, min_length=1, max_length=160)
    floor: str | None = Field(default=None, max_length=40)
    capacity: int | None = Field(default=None, gt=0, le=10000)
    description: str | None = Field(default=None, max_length=5000)
    facilities: list[str] | None = Field(default=None, max_length=100)
    operating_hours: dict[str, list[OperatingWindow]] | None = None
    room_status: str | None = Field(default=None, pattern="^(ACTIVE|INACTIVE|MAINTENANCE)$")
    photo_url: HttpUrl | None = None

    @model_validator(mode="after")
    def non_nullable_fields_cannot_be_null(self):
        for field_name in ("room_name", "building", "capacity", "facilities", "operating_hours", "room_status"):
            if field_name in self.model_fields_set and getattr(self, field_name) is None:
                raise ValueError(f"{field_name} cannot be null")
        return self


class RoomOut(BaseOut):
    id: UUID
    room_name: str
    room_code: str | None
    building: str
    floor: str | None
    capacity: int
    description: str | None
    facilities: list[str]
    operating_hours: dict[str, Any]
    room_status: str
    photo_url: str | None
    created_at: datetime
    updated_at: datetime


class AvailabilityIn(BaseModel):
    date: date
    start_time: time
    end_time: time
    participant_count: int = Field(gt=0)

    @model_validator(mode="after")
    def validate_period(self):
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be later than start_time; overnight bookings are not supported")
        return self


class AvailabilityOut(BaseModel):
    room_id: UUID
    available: bool
    reasons: list[str]
    checked_at: datetime


class ReservationCreateIn(AvailabilityIn):
    room_id: UUID
    purpose: str = Field(min_length=3, max_length=240)
    notes: str | None = Field(default=None, max_length=5000)


class ReservationRejectIn(BaseModel):
    rejection_reason: str = Field(min_length=3, max_length=2000)


class ReservationCancelIn(BaseModel):
    reason: str | None = Field(default=None, max_length=2000)


class ReservationOut(BaseOut):
    id: UUID
    user_id: UUID
    room_id: UUID
    purpose: str
    reservation_date: date
    start_time: time
    end_time: time
    participant_count: int
    notes: str | None
    status: ReservationStatus
    admin_id: UUID | None
    rejection_reason: str | None
    submitted_at: datetime
    approved_at: datetime | None
    cancelled_at: datetime | None
    cancellation_reason: str | None
    cancelled_by_id: UUID | None
    updated_at: datetime


class ScheduleCreateIn(BaseModel):
    room_id: UUID
    course_name: str = Field(min_length=2, max_length=200)
    schedule_date: date | None = None
    day_of_week: int | None = Field(default=None, ge=0, le=6)
    start_time: time
    end_time: time
    data_source: str = Field(default="ADMIN_MANUAL", min_length=2, max_length=240)

    @model_validator(mode="after")
    def validate_schedule(self):
        if (self.schedule_date is None) == (self.day_of_week is None):
            raise ValueError("Provide exactly one of schedule_date or day_of_week (Monday=0)")
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be later than start_time")
        return self


class ScheduleOut(BaseOut):
    id: UUID
    room_id: UUID
    course_name: str
    schedule_date: date | None
    day_of_week: int | None
    start_time: time
    end_time: time
    schedule_status: str
    data_source: str
    last_updated_at: datetime


class UnavailabilityCreateIn(BaseModel):
    room_id: UUID
    unavailable_date: date
    start_time: time
    end_time: time
    reason: str = Field(min_length=3, max_length=240)

    @model_validator(mode="after")
    def validate_window(self):
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be later than start_time")
        return self


class NotificationOut(BaseOut):
    id: UUID
    notification_type: str
    title: str
    message: str
    read_at: datetime | None
    delivery_status: str
    email_delivery_status: str
    email_sent_at: datetime | None
    created_at: datetime


class PageMeta(BaseModel):
    page: int
    limit: int
    total: int
    total_pages: int


def serialize_room(room) -> dict:
    return RoomOut.model_validate(room).model_dump(mode="json")


def serialize_reservation(reservation) -> dict:
    return ReservationOut.model_validate(reservation).model_dump(mode="json")


class ScheduleImportCommitIn(BaseModel):
    batch_id: UUID
