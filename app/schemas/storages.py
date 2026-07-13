from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class StorageCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    storage_type: str
    config: dict[str, Any]
    is_default: bool = False
    capacity_limit_bytes: int | None = Field(default=None, ge=0)


class StorageUpdate(BaseModel):
    name: str | None = None
    config: dict[str, Any] | None = None
    is_default: bool | None = None
    status: str | None = None
    capacity_limit_bytes: int | None = Field(default=None, ge=0)


class StorageRead(ORMModel):
    id: int
    name: str
    storage_type: str
    is_default: bool
    status: str
    capacity_limit_bytes: int | None = None
    created_by: int | None = None
    created_by_username: str | None = None
    created_at: datetime
    updated_at: datetime


class StorageTestResponse(BaseModel):
    ok: bool
    message: str


class StorageCapacityResponse(BaseModel):
    storage_id: int
    storage_name: str
    capacity_limit_bytes: int | None
    used_bytes: int
    usage_percent: float | None
