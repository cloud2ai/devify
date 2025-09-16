"""
EmailTask API Views

This module contains APIView classes for EmailTask model CRUD operations.
"""

import logging
from rest_framework import status, serializers
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from core.swagger import response, error_response, pagination_response

from .base import BaseAPIView
from ..models import EmailTask
from ..serializers import (
    EmailTaskSerializer,
    EmailTaskCreateSerializer,
    EmailTaskUpdateSerializer
)

logger = logging.getLogger(__name__)


class EmailTaskAPIView(BaseAPIView):
    """
    APIView for EmailTask CRUD operations
    """

    def get_queryset(self):
        """
        Get EmailTask queryset
        """
        return EmailTask.objects.all()

    @extend_schema(
        operation_id='email_tasks_list',
        summary='List email tasks',
        description='Get paginated list of user email tasks',
        parameters=[
            OpenApiParameter(
                name='status',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Filter by task status'
            ),
            OpenApiParameter(
                name='ordering',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Order by field (e.g., created_at, started_at)'
            )
        ],
        responses={
            200: pagination_response(EmailTaskSerializer),
            401: error_response()
        }
    )
    def get(self, request):
        """
        List user email tasks with pagination and filtering
        """
        try:
            queryset = self.filter_by_user(self.get_queryset())

            # Filter by status
            task_status = request.query_params.get('status', None)
            if task_status:
                queryset = queryset.filter(status=task_status)

            # Ordering
            ordering = request.query_params.get('ordering', '-created_at')
            if ordering:
                queryset = queryset.order_by(ordering)

            # Pagination
            page_size = min(int(request.query_params.get('page_size', 10)), 100)
            page = int(request.query_params.get('page', 1))

            start = (page - 1) * page_size
            end = start + page_size

            total = queryset.count()
            items = queryset[start:end]

            serializer = EmailTaskSerializer(items, many=True, context={'request': request})

            response_data = {
                'code': 200,
                'message': 'Email tasks retrieved successfully',
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
            logger.error(f"Error listing email tasks: {str(e)}")
            return Response({
                'code': 500,
                'message': 'Internal server error',
                'data': None
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @extend_schema(
        operation_id='email_tasks_create',
        summary='Create new email task',
        description='Create a new email processing task',
        request=EmailTaskCreateSerializer,
        responses={
            201: response(EmailTaskSerializer),
            400: error_response(),
            401: error_response()
        }
    )
    def post(self, request):
        """
        Create a new email task
        """
        try:
            serializer = EmailTaskCreateSerializer(
                data=request.data,
                context={'request': request}
            )

            if serializer.is_valid(raise_exception=True):
                task = serializer.save()
                response_serializer = EmailTaskSerializer(task, context={'request': request})

                return Response({
                    'code': 201,
                    'message': 'Email task created successfully',
                    'data': response_serializer.data
                }, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"Error creating email task: {str(e)}")
            return Response({
                'code': 400,
                'message': str(e),
                'data': None
            }, status=status.HTTP_400_BAD_REQUEST)


class EmailTaskDetailAPIView(BaseAPIView):
    """
    APIView for individual EmailTask operations
    """

    def get_queryset(self):
        """
        Get EmailTask queryset
        """
        return EmailTask.objects.all()

    @extend_schema(
        operation_id='email_tasks_retrieve',
        summary='Get email task details',
        description='Get details of a specific email task',
        responses={
            200: response(EmailTaskSerializer),
            404: error_response(),
            401: error_response()
        }
    )
    def get(self, request, pk):
        """
        Retrieve a specific email task
        """
        try:
            task = self.get_object(pk)
            serializer = EmailTaskSerializer(task, context={'request': request})

            return Response({
                'code': 200,
                'message': 'Email task retrieved successfully',
                'data': serializer.data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error retrieving email task {pk}: {str(e)}")
            return Response({
                'code': 404,
                'message': 'Email task not found',
                'data': None
            }, status=status.HTTP_404_NOT_FOUND)

    @extend_schema(
        operation_id='email_tasks_update',
        summary='Update email task',
        description='Update a specific email task',
        request=EmailTaskUpdateSerializer,
        responses={
            200: response(EmailTaskSerializer),
            400: error_response(),
            404: error_response(),
            401: error_response()
        }
    )
    def put(self, request, pk):
        """
        Update a specific email task (full update)
        """
        try:
            task = self.get_object(pk)
            serializer = EmailTaskUpdateSerializer(
                task,
                data=request.data,
                context={'request': request}
            )

            if serializer.is_valid(raise_exception=True):
                updated_task = serializer.save()
                response_serializer = EmailTaskSerializer(updated_task, context={'request': request})

                return Response({
                    'code': 200,
                    'message': 'Email task updated successfully',
                    'data': response_serializer.data
                }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error updating email task {pk}: {str(e)}")
            return Response({
                'code': 400,
                'message': str(e),
                'data': None
            }, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        operation_id='email_tasks_partial_update',
        summary='Partially update email task',
        description='Partially update a specific email task',
        request=EmailTaskUpdateSerializer,
        responses={
            200: response(EmailTaskSerializer),
            400: error_response(),
            404: error_response(),
            401: error_response()
        }
    )
    def patch(self, request, pk):
        """
        Partially update a specific email task
        """
        try:
            task = self.get_object(pk)
            serializer = EmailTaskUpdateSerializer(
                task,
                data=request.data,
                partial=True,
                context={'request': request}
            )

            if serializer.is_valid(raise_exception=True):
                updated_task = serializer.save()
                response_serializer = EmailTaskSerializer(updated_task, context={'request': request})

                return Response({
                    'code': 200,
                    'message': 'Email task updated successfully',
                    'data': response_serializer.data
                }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error updating email task {pk}: {str(e)}")
            return Response({
                'code': 400,
                'message': str(e),
                'data': None
            }, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        operation_id='email_tasks_delete',
        summary='Delete email task',
        description='Delete a specific email task',
        responses={
            204: error_response(),
            404: error_response(),
            401: error_response()
        }
    )
    def delete(self, request, pk):
        """
        Delete a specific email task
        """
        try:
            task = self.get_object(pk)
            task.delete()

            return Response({
                'code': 204,
                'message': 'Email task deleted successfully',
                'data': None
            }, status=status.HTTP_204_NO_CONTENT)

        except Exception as e:
            logger.error(f"Error deleting email task {pk}: {str(e)}")
            return Response({
                'code': 404,
                'message': 'Email task not found',
                'data': None
            }, status=status.HTTP_404_NOT_FOUND)
