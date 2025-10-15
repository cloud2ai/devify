"""
EmailMessage API Views

This module contains APIView classes for EmailMessage model CRUD operations.
"""

import logging
from rest_framework import status, serializers
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from core.swagger import response, error_response, pagination_response

from .base import BaseAPIView
from ..models import EmailMessage
from ..serializers import (
    EmailMessageSerializer,
    EmailMessageCreateSerializer,
    EmailMessageUpdateSerializer
)

logger = logging.getLogger(__name__)


class EmailMessageAPIView(BaseAPIView):
    """
    APIView for EmailMessage CRUD operations
    """

    def get_queryset(self):
        """
        Get EmailMessage queryset with related objects
        """
        return EmailMessage.objects.select_related('user').all()

    @extend_schema(
        operation_id='threadlines_list',
        summary='List threadlines',
        description='Get paginated list of user threadlines (email messages with attachments)',
        parameters=[
            OpenApiParameter(
                name='search',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Search in subject, sender, recipients fields'
            ),
            OpenApiParameter(
                name='status',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Filter by processing status'
            ),
            OpenApiParameter(
                name='ordering',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Order by field (e.g., received_at, created_at)'
            )
        ],
        responses={
            200: pagination_response(EmailMessageSerializer),
            401: error_response()
        }
    )
    def get(self, request):
        """
        List user threadlines with pagination and filtering
        """
        try:
            # Set request for base class methods
            self.request = request
            queryset = self.filter_by_user(self.get_queryset())

            # Search functionality
            search = request.query_params.get('search', None)
            if search:
                queryset = queryset.filter(
                    Q(subject__icontains=search) |
                    Q(sender__icontains=search) |
                    Q(recipients__icontains=search)
                )

            # Filter by status
            message_status = request.query_params.get('status', None)
            if message_status:
                queryset = queryset.filter(status=message_status)

            # Ordering
            ordering = request.query_params.get('ordering', '-received_at')
            if ordering:
                queryset = queryset.order_by(ordering)

            # Pagination
            page_size = min(int(request.query_params.get('page_size', 10)), 100)
            page = int(request.query_params.get('page', 1))

            start = (page - 1) * page_size
            end = start + page_size

            total = queryset.count()
            items = queryset[start:end]

            serializer = EmailMessageSerializer(items, many=True, context={'request': request})

            response_data = {
                'code': 200,
                'message': 'Threadlines retrieved successfully',
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
            logger.error(f"Error listing email messages: {str(e)}")
            return Response({
                'code': 500,
                'message': 'Internal server error',
                'data': None
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @extend_schema(
        operation_id='threadlines_create',
        summary='Create new threadline',
        description='Create a new threadline (email message with attachments)',
        request=EmailMessageCreateSerializer,
        responses={
            201: response(EmailMessageSerializer),
            400: error_response(),
            401: error_response()
        }
    )
    def post(self, request):
        """
        Create a new threadline
        """
        try:
            # Set request for base class methods
            self.request = request
            serializer = EmailMessageCreateSerializer(
                data=request.data,
                context={'request': request}
            )

            if serializer.is_valid(raise_exception=True):
                message = serializer.save()
                response_serializer = EmailMessageSerializer(message, context={'request': request})

                return Response({
                    'code': 201,
                    'message': 'Threadline created successfully',
                    'data': response_serializer.data
                }, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"Error creating email message: {str(e)}")
            return Response({
                'code': 400,
                'message': str(e),
                'data': None
            }, status=status.HTTP_400_BAD_REQUEST)


class EmailMessageDetailAPIView(BaseAPIView):
    """
    APIView for individual EmailMessage operations
    """

    def get_queryset(self):
        """
        Get EmailMessage queryset with related objects
        """
        return EmailMessage.objects.select_related('user').all()

    @extend_schema(
        operation_id='threadlines_retrieve',
        summary='Get threadline details',
        description='Get details of a specific threadline',
        responses={
            200: response(EmailMessageSerializer),
            404: error_response(),
            401: error_response()
        }
    )
    def get(self, request, pk):
        """
        Retrieve a specific threadline
        """
        try:
            message = self.get_object(pk)
            serializer = EmailMessageSerializer(message, context={'request': request})

            return Response({
                'code': 200,
                'message': 'Threadline retrieved successfully',
                'data': serializer.data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error retrieving threadline {pk}: {str(e)}")
            return Response({
                'code': 404,
                'message': 'Threadline not found',
                'data': None
            }, status=status.HTTP_404_NOT_FOUND)

    @extend_schema(
        operation_id='threadlines_update',
        summary='Update email message',
        description='Update a specific email message',
        request=EmailMessageUpdateSerializer,
        responses={
            200: response(EmailMessageSerializer),
            400: error_response(),
            404: error_response(),
            401: error_response()
        }
    )
    def put(self, request, pk):
        """
        Update a specific email message (full update)
        """
        try:
            message = self.get_object(pk)
            serializer = EmailMessageUpdateSerializer(
                message,
                data=request.data,
                context={'request': request}
            )

            if serializer.is_valid(raise_exception=True):
                updated_message = serializer.save()
                response_serializer = EmailMessageSerializer(updated_message, context={'request': request})

                return Response({
                    'code': 200,
                    'message': 'Email message updated successfully',
                    'data': response_serializer.data
                }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error updating email message {pk}: {str(e)}")
            return Response({
                'code': 400,
                'message': str(e),
                'data': None
            }, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        operation_id='email_messages_partial_update',
        summary='Partially update email message',
        description='Partially update a specific email message',
        request=EmailMessageUpdateSerializer,
        responses={
            200: response(EmailMessageSerializer),
            400: error_response(),
            404: error_response(),
            401: error_response()
        }
    )
    def patch(self, request, pk):
        """
        Partially update a specific email message
        """
        try:
            message = self.get_object(pk)
            serializer = EmailMessageUpdateSerializer(
                message,
                data=request.data,
                partial=True,
                context={'request': request}
            )

            if serializer.is_valid(raise_exception=True):
                updated_message = serializer.save()
                response_serializer = EmailMessageSerializer(updated_message, context={'request': request})

                return Response({
                    'code': 200,
                    'message': 'Email message updated successfully',
                    'data': response_serializer.data
                }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error updating email message {pk}: {str(e)}")
            return Response({
                'code': 400,
                'message': str(e),
                'data': None
            }, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        operation_id='threadlines_delete',
        summary='Delete email message',
        description='Delete a specific email message',
        responses={
            204: error_response(),
            404: error_response(),
            401: error_response()
        }
    )
    def delete(self, request, pk):
        """
        Delete a specific email message
        """
        try:
            message = self.get_object(pk)
            message.delete()

            return Response({
                'code': 204,
                'message': 'Email message deleted successfully',
                'data': None
            }, status=status.HTTP_204_NO_CONTENT)

        except Exception as e:
            logger.error(f"Error deleting email message {pk}: {str(e)}")
            return Response({
                'code': 404,
                'message': 'Email message not found',
                'data': None
            }, status=status.HTTP_404_NOT_FOUND)
