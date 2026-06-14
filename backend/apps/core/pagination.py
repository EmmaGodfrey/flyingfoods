"""Default pagination: page-number with client-tunable page size."""

from rest_framework.pagination import PageNumberPagination


class DefaultPageNumberPagination(PageNumberPagination):
    """Standard pagination for every list endpoint."""

    page_size = 25
    page_size_query_param = "page_size"
    max_page_size = 200
