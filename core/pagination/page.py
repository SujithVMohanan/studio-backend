from typing import Any
from urllib.parse import urlparse

from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from core.responses import ResponseInfo


class RestPagination(PageNumberPagination):

    page_size               = 20
    page_size_query_param   = "limit"
    max_page_size           = 100
    page_query_param        = "page"

    def get_paginated_response(self, data: Any) -> Response:
        assert self.page is not None
        payload = {
            "links": {
                "next": self._relative_url(self.get_next_link()),
                "previous": self._relative_url(self.get_previous_link()),
            },
            "count": self.page.paginator.count,
            "results": data,
        }
        return ResponseInfo.ok(payload, message="Data retrieved successfully")

    @staticmethod
    def _relative_url(url: str | None) -> str:
        if not url:
            return ""
        parsed = urlparse(url)
        if parsed.query:
            return f"{parsed.path}?{parsed.query}"
        return parsed.path
