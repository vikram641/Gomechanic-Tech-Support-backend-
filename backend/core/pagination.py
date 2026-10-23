from typing import Annotated

from fastapi import Query

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 200


class PageParams:
    def __init__(self, page: int, page_size: int):
        self.page = page
        self.page_size = page_size
        self.skip = (page - 1) * page_size


def page_params(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = DEFAULT_PAGE_SIZE,
) -> PageParams:
    return PageParams(page, page_size)


def build_page(items, total_count: int, page: int, page_size: int) -> dict:
    """Build the {count, page, page_size, total_pages, results} envelope,
    matching the previous DRF DefaultPagination.get_paginated_response."""
    total_pages = max((total_count + page_size - 1) // page_size, 1)
    return {
        "count": total_count,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "results": items,
    }
