"""
Custom pagination classes for DonorCRM API.
"""
from rest_framework.pagination import PageNumberPagination


class StandardPagination(PageNumberPagination):
    """
    Standard pagination for list endpoints.
    """
    page_size = 25
    page_size_query_param = 'page_size'
    max_page_size = 100


class LargePagination(PageNumberPagination):
    """
    Larger pagination for export-like operations.
    """
    page_size = 100
    page_size_query_param = 'page_size'
    max_page_size = 500
