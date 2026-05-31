from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Page(BaseModel, Generic[T]):
    items: list[T]
    page: int
    page_size: int
    total: int


class Message(BaseModel):
    message: str


def validate_password(value: str) -> str:
    if len(value) < 5:
        raise ValueError("password must be at least 5 characters")
    if not any(c.isalpha() for c in value):
        raise ValueError("password must contain at least one letter")
    if not any(c.isdigit() for c in value):
        raise ValueError("password must contain at least one digit")
    return value

