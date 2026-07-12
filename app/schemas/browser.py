from typing import Any

from pydantic import BaseModel


class CatalogRead(BaseModel):
    name: str


class TableRead(BaseModel):
    schema_name: str
    name: str
    type: str


class ColumnRead(BaseModel):
    name: str
    data_type: str
    nullable: bool
    default: str | None = None
    primary_key: bool = False


class RowPage(BaseModel):
    columns: list[str]
    rows: list[list[Any]]
    page: int
    page_size: int
    total: int
