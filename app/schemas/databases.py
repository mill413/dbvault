from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class K8sConfigSchema(BaseModel):
    namespace: str = "default"
    pod_name: str | None = None
    label_selector: str | None = None
    container: str | None = None
    kubeconfig: str | None = None
    context: str | None = None


class DatabaseCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    db_type: str
    host: str = "localhost"
    port: int = Field(default=3306, gt=0, le=65535)
    username: str
    password: str
    database_name: str | None = None
    ssl_enabled: bool = False
    ssl_config: dict[str, Any] | None = None
    environment: str = "prod"
    owner: str | None = None
    tags: list[str] = []
    description: str | None = None
    connection_type: str = "direct"
    k8s_config: K8sConfigSchema | None = None


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
    connection_type: str | None = None
    k8s_config: K8sConfigSchema | None = None


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
    connection_type: str = "direct"
    k8s_config: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime


class DatabaseTestRequest(DatabaseCreate):
    pass


class ConnectionTestResponse(BaseModel):
    ok: bool
    version: str | None = None
    duration_seconds: float
    message: str | None = None
