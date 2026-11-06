from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


class UserCreate(BaseModel):
    email: str = Field(pattern=EMAIL_PATTERN, max_length=255)
    full_name: str = Field(min_length=2, max_length=160)
    password: str = Field(min_length=8, max_length=128)


class UserRead(BaseModel):
    id: int
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LoginRequest(BaseModel):
    email: str = Field(pattern=EMAIL_PATTERN, max_length=255)
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead


class AppointmentCreate(BaseModel):
    starts_at: datetime
    ends_at: datetime
    reason: str = Field(min_length=3, max_length=500)

    @field_validator("starts_at", "ends_at")
    @classmethod
    def normalize_datetime(cls, value: datetime) -> datetime:
        if value.tzinfo:
            return value.astimezone(timezone.utc).replace(tzinfo=None)
        return value

    @model_validator(mode="after")
    def validate_interval(self):
        if self.ends_at <= self.starts_at:
            raise ValueError("ends_at must be after starts_at")
        if self.starts_at <= datetime.now(timezone.utc).replace(tzinfo=None):
            raise ValueError("Appointment must be in the future")
        if (self.ends_at - self.starts_at).total_seconds() > 8 * 3600:
            raise ValueError("Appointment duration cannot exceed 8 hours")
        return self


class AppointmentUpdate(BaseModel):
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    reason: str | None = Field(default=None, min_length=3, max_length=500)
    status: Literal["pending", "approved", "completed", "cancelled"] | None = None

    @field_validator("starts_at", "ends_at")
    @classmethod
    def normalize_datetime(cls, value: datetime | None) -> datetime | None:
        if value and value.tzinfo:
            return value.astimezone(timezone.utc).replace(tzinfo=None)
        return value

    @model_validator(mode="after")
    def reject_null_updates(self):
        if any(getattr(self, field) is None for field in self.model_fields_set):
            raise ValueError("Update fields cannot be null")
        return self


class AppointmentRead(BaseModel):
    id: int
    patient_id: int
    starts_at: datetime
    ends_at: datetime
    reason: str
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EnquiryCreate(BaseModel):
    subject: str = Field(min_length=3, max_length=200)
    message: str = Field(min_length=5, max_length=10000)


class EnquiryUpdate(BaseModel):
    subject: str | None = Field(default=None, min_length=3, max_length=200)
    message: str | None = Field(default=None, min_length=5, max_length=10000)
    status: Literal["open", "in_progress", "resolved", "closed"] | None = None
    review_status: Literal["pending", "approved", "rejected"] | None = None

    @model_validator(mode="after")
    def reject_null_updates(self):
        if any(getattr(self, field) is None for field in self.model_fields_set):
            raise ValueError("Update fields cannot be null")
        return self


class EnquiryRead(BaseModel):
    id: int
    patient_id: int
    subject: str
    message: str
    category: str
    summary: str
    intent: str
    suggested_response: str
    review_status: str
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentRead(BaseModel):
    id: int
    filename: str
    status: str
    processing_error: str | None
    content_hash: str | None
    page_count: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConversationCreate(BaseModel):
    title: str = Field(default="New conversation", min_length=1, max_length=200)


class ConversationRead(BaseModel):
    id: int
    patient_id: int
    title: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=4000)


class MessageRead(BaseModel):
    id: int
    conversation_id: int
    role: str
    content: str
    sources: list[str] = Field(default_factory=list)
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AvailableSlot(BaseModel):
    starts_at: datetime
    ends_at: datetime


class DocumentSummary(BaseModel):
    document_id: int
    filename: str
    summary: str
    source_pages: list[int] = Field(default_factory=list)
