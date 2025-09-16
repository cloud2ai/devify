"""
Settings API Views

This module contains APIView classes for Settings model CRUD operations.
"""

import logging
from typing import Any, Dict, List, Optional
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from rest_framework import status, serializers
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from core.swagger import response, error_response, pagination_response, pagination_params, ordering_param, search_param

from .base import BaseAPIView
from ..models import Settings
from ..serializers import (
    SettingsSerializer,
    SettingsCreateSerializer,
    SettingsUpdateSerializer
)

logger = logging.getLogger(__name__)


class SettingsAPIView(BaseAPIView):
    """
    APIView for Settings CRUD operations

    Provides endpoints for listing, creating, retrieving, updating,
    and deleting user settings with proper authentication and
    authorization controls.
    """

    def get_queryset(self):
        """
        Get Settings queryset with select_related optimization

        Returns:
            QuerySet: Settings queryset with user relationship optimized
        """
        return Settings.objects.select_related('user').all()

    def _handle_error(self, error: Exception, operation: str,
                     pk: Optional[int] = None) -> Response:
        """
        Handle common error scenarios with consistent response format

        Args:
            error: The exception that occurred
            operation: Description of the operation being performed
            pk: Optional primary key for context

        Returns:
            Response: Standardized error response
        """
        pk_context = f" {pk}" if pk else ""
        logger.error(f"Error {operation}{pk_context}: {str(error)}")

        # Determine appropriate status code based on error type
        if 'No Settings matches the given query' in str(error):
            status_code = status.HTTP_404_NOT_FOUND
            error_code = 404
        elif 'UNIQUE constraint failed' in str(error):
            status_code = status.HTTP_400_BAD_REQUEST
            error_code = 400
        else:
            status_code = status.HTTP_400_BAD_REQUEST
            error_code = 400

        return Response({
            'code': error_code,
            'message': str(error),
            'data': None
        }, status=status_code)

    @extend_schema(
        operation_id='settings_list',
        summary='List user settings',
        description='Get paginated list of user settings',
        parameters=pagination_params() + [
            search_param(),
            OpenApiParameter(
                name='is_active',
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
                description='Filter by active status'
            ),
            ordering_param('key')
        ],
        responses={
            200: pagination_response(SettingsSerializer),
            401: error_response()
        }
    )
    def get(self, request) -> Response:
        """
        List user settings with pagination and filtering

        Supports search by key/description, filtering by active status,
        and custom ordering with pagination.

        Args:
            request: HTTP request object

        Returns:
            Response: Paginated list of user settings
        """
        try:
            queryset = self.filter_by_user(self.get_queryset())

            # Search functionality
            search = request.query_params.get('search')
            if search:
                queryset = queryset.filter(
                    Q(key__icontains=search) |
                    Q(description__icontains=search)
                )

            # Filter by active status
            is_active = request.query_params.get('is_active')
            if is_active is not None:
                queryset = queryset.filter(
                    is_active=is_active.lower() == 'true'
                )

            # Ordering
            ordering = request.query_params.get('ordering', 'key')
            if ordering:
                queryset = queryset.order_by(ordering)

            # Pagination
            page_size = min(int(request.query_params.get('page_size', 10)), 100)
            page = int(request.query_params.get('page', 1))

            start = (page - 1) * page_size
            end = start + page_size

            total = queryset.count()
            items = queryset[start:end]

            serializer = SettingsSerializer(
                items,
                many=True,
                context={'request': request}
            )

            response_data = {
                'code': 200,
                'message': 'Settings retrieved successfully',
                'data': {
                    'list': serializer.data,
                    'pagination': {
                        'total': total,
                        'page': page,
                        'pageSize': page_size,
                        'next': f"?page={page + 1}&page_size={page_size}" if end < total else None,
                        'previous': f"?page={page - 1}&page_size={page_size}" if page > 1 else None
                    }
                }
            }

            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            return self._handle_error(e, "listing settings")

    @extend_schema(
        operation_id='settings_create',
        summary='Create new setting',
        description='Create a new user setting',
        request=SettingsCreateSerializer,
        responses={
            201: response(SettingsSerializer),
            400: error_response(),
            401: error_response()
        }
    )
    def post(self, request) -> Response:
        """
        Create a new setting

        Creates a new setting for the authenticated user with
        validation and proper error handling.

        Args:
            request: HTTP request object containing setting data

        Returns:
            Response: Created setting data or error response
        """
        try:
            serializer = SettingsCreateSerializer(
                data=request.data,
                context={'request': request}
            )

            if serializer.is_valid(raise_exception=True):
                setting = serializer.save()
                response_serializer = SettingsSerializer(
                    setting,
                    context={'request': request}
                )

                return Response({
                    'code': 201,
                    'message': 'Setting created successfully',
                    'data': response_serializer.data
                }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return self._handle_error(e, "creating setting")


class SettingsDetailAPIView(BaseAPIView):
    """
    APIView for individual Settings operations

    Provides endpoints for retrieving, updating, and deleting
    specific settings by ID with proper authorization controls.
    """

    def get_queryset(self):
        """
        Get Settings queryset with select_related optimization

        Returns:
            QuerySet: Settings queryset with user relationship optimized
        """
        return Settings.objects.select_related('user').all()

    def _handle_error(self, error: Exception, operation: str,
                     pk: Optional[int] = None) -> Response:
        """
        Handle common error scenarios with consistent response format

        Args:
            error: The exception that occurred
            operation: Description of the operation being performed
            pk: Optional primary key for context

        Returns:
            Response: Standardized error response
        """
        pk_context = f" {pk}" if pk else ""
        logger.error(f"Error {operation}{pk_context}: {str(error)}")

        # Determine appropriate status code based on error type
        if 'No Settings matches the given query' in str(error):
            status_code = status.HTTP_404_NOT_FOUND
            error_code = 404
        elif 'UNIQUE constraint failed' in str(error):
            status_code = status.HTTP_400_BAD_REQUEST
            error_code = 400
        else:
            status_code = status.HTTP_400_BAD_REQUEST
            error_code = 400

        return Response({
            'code': error_code,
            'message': str(error),
            'data': None
        }, status=status_code)

    @extend_schema(
        operation_id='settings_retrieve',
        summary='Get setting details',
        description='Get details of a specific setting',
        responses={
            200: response(SettingsSerializer),
            404: error_response(),
            401: error_response()
        }
    )
    def get(self, request, pk: int) -> Response:
        """
        Retrieve a specific setting

        Gets a single setting by ID with proper authorization
        to ensure users can only access their own settings.

        Args:
            request: HTTP request object
            pk: Primary key of the setting to retrieve

        Returns:
            Response: Setting data or error response
        """
        try:
            setting = self.get_object(pk)
            serializer = SettingsSerializer(
                setting,
                context={'request': request}
            )

            return Response({
                'code': 200,
                'message': 'Setting retrieved successfully',
                'data': serializer.data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return self._handle_error(e, "retrieving setting", pk)

    @extend_schema(
        operation_id='settings_update',
        summary='Update setting',
        description='Update a specific setting',
        request=SettingsUpdateSerializer,
        responses={
            200: response(SettingsSerializer),
            400: error_response(),
            404: error_response(),
            401: error_response()
        }
    )
    def put(self, request, pk: int) -> Response:
        """
        Update a specific setting (full update)

        Performs a complete update of the setting with all fields
        required. Validates data and ensures proper authorization.

        Args:
            request: HTTP request object containing updated data
            pk: Primary key of the setting to update

        Returns:
            Response: Updated setting data or error response
        """
        try:
            setting = self.get_object(pk)
            serializer = SettingsUpdateSerializer(
                setting,
                data=request.data,
                context={'request': request}
            )

            if serializer.is_valid(raise_exception=True):
                updated_setting = serializer.save()
                response_serializer = SettingsSerializer(
                    updated_setting,
                    context={'request': request}
                )

                return Response({
                    'code': 200,
                    'message': 'Setting updated successfully',
                    'data': response_serializer.data
                }, status=status.HTTP_200_OK)

        except Exception as e:
            return self._handle_error(e, "updating setting", pk)

    @extend_schema(
        operation_id='settings_partial_update',
        summary='Partially update setting',
        description='Partially update a specific setting',
        request=SettingsUpdateSerializer,
        responses={
            200: response(SettingsSerializer),
            400: error_response(),
            404: error_response(),
            401: error_response()
        }
    )
    def patch(self, request, pk: int) -> Response:
        """
        Partially update a specific setting

        Performs a partial update of the setting allowing only
        specific fields to be updated. Validates data and ensures
        proper authorization.

        Args:
            request: HTTP request object containing partial data
            pk: Primary key of the setting to update

        Returns:
            Response: Updated setting data or error response
        """
        try:
            setting = self.get_object(pk)
            serializer = SettingsUpdateSerializer(
                setting,
                data=request.data,
                partial=True,
                context={'request': request}
            )

            if serializer.is_valid(raise_exception=True):
                updated_setting = serializer.save()
                response_serializer = SettingsSerializer(
                    updated_setting,
                    context={'request': request}
                )

                return Response({
                    'code': 200,
                    'message': 'Setting updated successfully',
                    'data': response_serializer.data
                }, status=status.HTTP_200_OK)

        except Exception as e:
            return self._handle_error(e, "updating setting", pk)

    @extend_schema(
        operation_id='settings_delete',
        summary='Delete setting',
        description='Delete a specific setting',
        responses={
            204: error_response(),
            404: error_response(),
            401: error_response()
        }
    )
    def delete(self, request, pk: int) -> Response:
        """
        Delete a specific setting

        Permanently deletes a setting by ID with proper authorization
        to ensure users can only delete their own settings.

        Args:
            request: HTTP request object
            pk: Primary key of the setting to delete

        Returns:
            Response: Success confirmation or error response
        """
        try:
            setting = self.get_object(pk)
            setting.delete()

            return Response({
                'code': 204,
                'message': 'Setting deleted successfully',
                'data': None
            }, status=status.HTTP_204_NO_CONTENT)

        except Exception as e:
            return self._handle_error(e, "deleting setting", pk)
