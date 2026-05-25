from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class StorageCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    storage_type: str
    config: dict[str, Any]
    is_default: bool = False


class StorageUpdate(BaseModel):
    name: str | None = None
    config: dict[str, Any] | None = None
    is_default: bool | None = None
    status: str | None = None


class StorageRead(ORMModel):
    id: int
    name: str
    storage_type: str
    is_default: bool
    status: str
    created_at: datetime
    updated_at: datetime


class StorageTestResponse(BaseModel):
    ok: bool
    message: str

