"""
EmailAttachment API Views

This module contains APIView classes for EmailAttachment model CRUD operations.
"""

import logging
from rest_framework import status, serializers
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from core.swagger import response, error_response, pagination_response

from .base import BaseAPIView
from ..models import EmailAttachment
from ..serializers import (
    EmailAttachmentSerializer,
    EmailAttachmentCreateSerializer,
    EmailAttachmentUpdateSerializer
)

logger = logging.getLogger(__name__)


class EmailAttachmentAPIView(BaseAPIView):
    """
    APIView for EmailAttachment CRUD operations
    """

    def get_queryset(self):
        """
        Get EmailAttachment queryset with related objects
        """
        return EmailAttachment.objects.select_related('email_message').all()

    def filter_by_user(self, queryset):
        """
        Filter attachments by user through email message
        """
        return queryset.filter(email_message__user=self.request.user)

    @extend_schema(
        operation_id='email_attachments_list',
        summary='List email attachments',
        description='Get paginated list of user email attachments',
        parameters=[
            OpenApiParameter(
                name='search',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Search in filename, content_type fields'
            ),
            OpenApiParameter(
                name='status',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Filter by processing status'
            ),
            OpenApiParameter(
                name='email_message_id',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Filter by email message ID'
            ),
            OpenApiParameter(
                name='content_type',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Filter by content type'
            ),
            OpenApiParameter(
                name='ordering',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Order by field (e.g., filename, created_at)'
            )
        ],
        responses={
            200: pagination_response(EmailAttachmentSerializer),
            401: error_response()
        }
    )
    def get(self, request):
        """
        List user email attachments with pagination and filtering
        """
        try:
            queryset = self.filter_by_user(self.get_queryset())

            # Search functionality
            search = request.query_params.get('search', None)
            if search:
                queryset = queryset.filter(
                    Q(filename__icontains=search) |
                    Q(content_type__icontains=search)
                )

            # Filter by status
            attachment_status = request.query_params.get('status', None)
            if attachment_status:
                queryset = queryset.filter(status=attachment_status)

            # Filter by email message
            email_message_id = request.query_params.get('email_message_id', None)
            if email_message_id:
                queryset = queryset.filter(email_message_id=email_message_id)

            # Filter by content type
            content_type = request.query_params.get('content_type', None)
            if content_type:
                queryset = queryset.filter(content_type__icontains=content_type)

            # Ordering
            ordering = request.query_params.get('ordering', 'filename')
            if ordering:
                queryset = queryset.order_by(ordering)

            # Pagination
            page_size = min(int(request.query_params.get('page_size', 10)), 100)
            page = int(request.query_params.get('page', 1))

            start = (page - 1) * page_size
            end = start + page_size

            total = queryset.count()
            items = queryset[start:end]

            serializer = EmailAttachmentSerializer(items, many=True, context={'request': request})

            response_data = {
                'code': 200,
                'message': 'Email attachments retrieved successfully',
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
            logger.error(f"Error listing email attachments: {str(e)}")
            return Response({
                'code': 500,
                'message': 'Internal server error',
                'data': None
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @extend_schema(
        operation_id='email_attachments_create',
        summary='Create new email attachment',
        description='Create a new email attachment',
        request=EmailAttachmentCreateSerializer,
        responses={
            201: response(EmailAttachmentSerializer),
            400: error_response(),
            401: error_response()
        }
    )
    def post(self, request):
        """
        Create a new email attachment
        """
        try:
            serializer = EmailAttachmentCreateSerializer(
                data=request.data,
                context={'request': request}
            )

            if serializer.is_valid(raise_exception=True):
                attachment = serializer.save()
                response_serializer = EmailAttachmentSerializer(attachment, context={'request': request})

                return Response({
                    'code': 201,
                    'message': 'Email attachment created successfully',
                    'data': response_serializer.data
                }, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"Error creating email attachment: {str(e)}")
            return Response({
                'code': 400,
                'message': str(e),
                'data': None
            }, status=status.HTTP_400_BAD_REQUEST)


class EmailAttachmentDetailAPIView(BaseAPIView):
    """
    APIView for individual EmailAttachment operations
    """

    def get_queryset(self):
        """
        Get EmailAttachment queryset with related objects
        """
        return EmailAttachment.objects.select_related('email_message').all()

    def filter_by_user(self, queryset):
        """
        Filter attachments by user through email message
        """
        return queryset.filter(email_message__user=self.request.user)

    @extend_schema(
        operation_id='email_attachments_retrieve',
        summary='Get email attachment details',
        description='Get details of a specific email attachment',
        responses={
            200: response(EmailAttachmentSerializer),
            404: error_response(),
            401: error_response()
        }
    )
    def get(self, request, pk):
        """
        Retrieve a specific email attachment
        """
        try:
            attachment = self.get_object(pk)
            serializer = EmailAttachmentSerializer(attachment, context={'request': request})

            return Response({
                'code': 200,
                'message': 'Email attachment retrieved successfully',
                'data': serializer.data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error retrieving email attachment {pk}: {str(e)}")
            return Response({
                'code': 404,
                'message': 'Email attachment not found',
                'data': None
            }, status=status.HTTP_404_NOT_FOUND)

    @extend_schema(
        operation_id='email_attachments_update',
        summary='Update email attachment',
        description='Update a specific email attachment',
        request=EmailAttachmentUpdateSerializer,
        responses={
            200: response(EmailAttachmentSerializer),
            400: error_response(),
            404: error_response(),
            401: error_response()
        }
    )
    def put(self, request, pk):
        """
        Update a specific email attachment (full update)
        """
        try:
            attachment = self.get_object(pk)
            serializer = EmailAttachmentUpdateSerializer(
                attachment,
                data=request.data,
                context={'request': request}
            )

            if serializer.is_valid(raise_exception=True):
                updated_attachment = serializer.save()
                response_serializer = EmailAttachmentSerializer(updated_attachment, context={'request': request})

                return Response({
                    'code': 200,
                    'message': 'Email attachment updated successfully',
                    'data': response_serializer.data
                }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error updating email attachment {pk}: {str(e)}")
            return Response({
                'code': 400,
                'message': str(e),
                'data': None
            }, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        operation_id='email_attachments_partial_update',
        summary='Partially update email attachment',
        description='Partially update a specific email attachment',
        request=EmailAttachmentUpdateSerializer,
        responses={
            200: response(EmailAttachmentSerializer),
            400: error_response(),
            404: error_response(),
            401: error_response()
        }
    )
    def patch(self, request, pk):
        """
        Partially update a specific email attachment
        """
        try:
            attachment = self.get_object(pk)
            serializer = EmailAttachmentUpdateSerializer(
                attachment,
                data=request.data,
                partial=True,
                context={'request': request}
            )

            if serializer.is_valid(raise_exception=True):
                updated_attachment = serializer.save()
                response_serializer = EmailAttachmentSerializer(updated_attachment, context={'request': request})

                return Response({
                    'code': 200,
                    'message': 'Email attachment updated successfully',
                    'data': response_serializer.data
                }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error updating email attachment {pk}: {str(e)}")
            return Response({
                'code': 400,
                'message': str(e),
                'data': None
            }, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        operation_id='email_attachments_delete',
        summary='Delete email attachment',
        description='Delete a specific email attachment',
        responses={
            204: error_response(),
            404: error_response(),
            401: error_response()
        }
    )
    def delete(self, request, pk):
        """
        Delete a specific email attachment
        """
        try:
            attachment = self.get_object(pk)
            attachment.delete()

            return Response({
                'code': 204,
                'message': 'Email attachment deleted successfully',
                'data': None
            }, status=status.HTTP_204_NO_CONTENT)

        except Exception as e:
            logger.error(f"Error deleting email attachment {pk}: {str(e)}")
            return Response({
                'code': 404,
                'message': 'Email attachment not found',
                'data': None
            }, status=status.HTTP_404_NOT_FOUND)
