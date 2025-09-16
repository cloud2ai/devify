"""
Base APIView class for Threadline models

This module contains the BaseAPIView class that provides common functionality
for all Threadline APIView classes, including user filtering, object retrieval,
and common patterns.
"""

import logging
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

logger = logging.getLogger(__name__)


class BaseAPIView(APIView):
    """
    Base APIView with common functionality for all Threadline models

    This class provides:
    - Authentication requirement (IsAuthenticated)
    - User-based filtering for querysets
    - Object retrieval with user ownership validation
    - Common error handling patterns
    """

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Get queryset for the model

        Must be implemented by subclasses

        Returns:
            QuerySet: The base queryset for the model
        """
        raise NotImplementedError("Subclasses must implement get_queryset")

    def filter_by_user(self, queryset):
        """
        Filter queryset by current user

        This method can be overridden by subclasses for models that have
        different user relationship patterns (e.g., through foreign keys)

        Args:
            queryset: The queryset to filter

        Returns:
            QuerySet: Filtered queryset containing only user's objects
        """
        return queryset.filter(user=self.request.user)

    def get_object(self, pk):
        """
        Get object by primary key, ensuring user ownership

        Args:
            pk: Primary key of the object to retrieve

        Returns:
            Model instance: The requested object

        Raises:
            Http404: If object doesn't exist or doesn't belong to user
        """
        queryset = self.filter_by_user(self.get_queryset())
        return get_object_or_404(queryset, pk=pk)
