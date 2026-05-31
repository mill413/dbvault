from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.schemas.common import ORMModel, validate_password


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str

    @field_validator("password")
    @classmethod
    def check_password(cls, v: str) -> str:
        return validate_password(v)
    display_name: str | None = None
    email: EmailStr | None = None
    role: str = "Viewer"


class UserUpdate(BaseModel):
    display_name: str | None = None
    email: EmailStr | None = None
    role: str | None = None
    status: str | None = None


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

