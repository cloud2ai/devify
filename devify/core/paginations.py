"""
Custom pagination classes for the API.

This module provides pagination classes that match the standard API response format
with message field and clear pagination structure.
"""

from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from utils.constrants import SUCCESS_CODE


class APIPagination(PageNumberPagination):
    """
    Custom pagination class that matches the standard API response format.

    Response format:
    {
        "code": 0,
        "message": "success",
        "data": {
            "list": [...],
            "pagination": {
                "total": 100,
                "page": 1,
                "pageSize": 10,
                "next": "http://...",
                "previous": null
            }
        }
    }
    """

    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100
    page_query_param = 'page'

    def get_paginated_response(self, data):
        """
        Return paginated response in the standard API format.
        """
        return Response({
            "code": SUCCESS_CODE,
            "message": "success",
            "data": {
                "list": data,
                "pagination": {
                    "total": self.page.paginator.count,
                    "page": self.page.number,
                    "pageSize": self.get_page_size(self.request),
                    "next": self.get_next_link(),
                    "previous": self.get_previous_link()
                }
            }
        })