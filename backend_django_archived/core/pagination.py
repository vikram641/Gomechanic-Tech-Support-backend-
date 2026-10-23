from collections import OrderedDict

from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 200


def get_skip_limit(request, default_page_size=DEFAULT_PAGE_SIZE, max_page_size=MAX_PAGE_SIZE):
    """Compute Mongo skip/limit plus the page/page_size actually used, from
    DRF-style `page` and `page_size` query params."""

    def _parse_int(value, default, minimum=1):
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            return default
        return max(parsed, minimum)

    page = _parse_int(request.query_params.get("page"), 1)
    page_size = min(
        _parse_int(request.query_params.get("page_size"), default_page_size),
        max_page_size,
    )
    skip = (page - 1) * page_size
    return skip, page_size, page


class DefaultPagination(PageNumberPagination):
    """Paginates a plain Python list of already-serialized dicts.

    Views that query Mongo directly build this list themselves (skip/limit
    applied in the repository layer) and pass (items, total_count) through
    `paginate_list` rather than using DRF's queryset-based `paginate_queryset`.
    """

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 200

    def paginate_list(self, request, items, total_count):
        self.request = request
        page_size = self.get_page_size(request)
        try:
            page_number = int(request.query_params.get(self.page_query_param, 1))
        except (TypeError, ValueError):
            page_number = 1
        self.page = max(page_number, 1)
        self.page_size_used = page_size
        self.total_count = total_count
        return items

    def get_paginated_response(self, data):
        total_pages = max((self.total_count + self.page_size_used - 1) // self.page_size_used, 1)
        return Response(
            OrderedDict(
                [
                    ("count", self.total_count),
                    ("page", self.page),
                    ("page_size", self.page_size_used),
                    ("total_pages", total_pages),
                    ("results", data),
                ]
            )
        )
