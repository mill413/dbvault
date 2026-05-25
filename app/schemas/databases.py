from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class DatabaseCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    db_type: str
    host: str
    port: int = Field(gt=0, le=65535)
    username: str
    password: str
    database_name: str | None = None
    ssl_enabled: bool = False
    ssl_config: dict[str, Any] | None = None
    environment: str = "prod"
    owner: str | None = None
    tags: list[str] = []
    description: str | None = None


class DatabaseUpdate(BaseModel):
    name: str | None = None
    host: str | None = None
    port: int | None = Field(default=None, gt=0, le=65535)
    username: str | None = None
    password: str | None = None
    database_name: str | None = None
    ssl_enabled: bool | None = None
    ssl_config: dict[str, Any] | None = None
    environment: str | None = None
    owner: str | None = None
    tags: list[str] | None = None
    description: str | None = None


class DatabaseRead(ORMModel):
    id: int
    name: str
    db_type: str
    host: str
    port: int
    username: str
    database_name: str | None = None
    ssl_enabled: bool
    ssl_config: dict[str, Any] | None = None
    environment: str
    owner: str | None = None
    tags: list[str]
    description: str | None = None
    created_at: datetime
    updated_at: datetime


class DatabaseTestRequest(DatabaseCreate):
    pass


class ConnectionTestResponse(BaseModel):
    ok: bool
    version: str | None = None
    duration_seconds: float
    message: str | None = None

