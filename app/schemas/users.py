from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.schemas.common import ORMModel, validate_password

UserRole = Literal["Admin", "User"]


def _empty_email_to_none(value: str | None) -> str | None:
    if value == "":
        return None
    return value


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str

    @field_validator("password")
    @classmethod
    def check_password(cls, v: str) -> str:
        return validate_password(v)

    display_name: str | None = None
    email: EmailStr | None = None
    role: UserRole = "User"

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, v: str | None) -> str | None:
        return _empty_email_to_none(v)


class UserUpdate(BaseModel):
    display_name: str | None = None
    email: EmailStr | None = None
    role: UserRole | None = None
    status: str | None = None

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, v: str | None) -> str | None:
        return _empty_email_to_none(v)


class UserRead(ORMModel):
    id: int
    username: str
    display_name: str | None = None
    email: str | None = None
    role: str
    status: str
    last_login_at: datetime | None = None
    created_at: datetime


class ResetPasswordRequest(BaseModel):
    password: str

    @field_validator("password")
    @classmethod
    def check_password(cls, v: str) -> str:
        return validate_password(v)
