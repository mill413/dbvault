from dataclasses import dataclass

from fastapi import Query


@dataclass(frozen=True)
class Pagination:
    page: int
    page_size: int


def pagination_params(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> Pagination:
    return Pagination(page=page, page_size=page_size)
