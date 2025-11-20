"""
EmailTodo API Views

This module contains APIView classes for EmailTodo model CRUD operations.
"""

import logging

from django.db.models import Count
from rest_framework import status, serializers
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema
from core.swagger import (
    response, error_response, pagination_response,
    pagination_params, ordering_param, search_param
)

from .base import BaseAPIView
from ..models import EmailTodo
from ..serializers import (
    EmailTodoSerializer,
    EmailTodoListSerializer,
    EmailTodoFilterSerializer
)

logger = logging.getLogger(__name__)


class EmailTodoAPIView(BaseAPIView):
    """
    APIView for EmailTodo CRUD operations
    """

    def get_queryset(self):
        """
        Get EmailTodo queryset with related objects
        """
        return EmailTodo.objects.select_related(
            'user', 'email_message'
        ).all()

    @extend_schema(
        operation_id='todos_list',
        summary='List TODOs',
        description='Get paginated list of user TODOs with filtering',
        parameters=pagination_params() + [
            search_param(),
            EmailTodoFilterSerializer,
            ordering_param('-created_at')
        ],
        responses={
            200: pagination_response(EmailTodoListSerializer),
            401: error_response()
        }
    )
    def get(self, request):
        """
        List user TODOs with pagination and filtering
        """
        try:
            queryset = self.filter_by_user(self.get_queryset())

            # Filter by completion status
            is_completed = request.query_params.get('is_completed')
            if is_completed is not None:
                is_completed_bool = is_completed.lower() == 'true'
                queryset = queryset.filter(is_completed=is_completed_bool)

            # Filter by email message
            email_message_id = request.query_params.get('email_message_id')
            if email_message_id:
                queryset = queryset.filter(email_message_id=email_message_id)

            # Filter by priority
            priority = request.query_params.get('priority')
            if priority:
                queryset = queryset.filter(priority=priority.lower())

            # Filter by owner
            owner = request.query_params.get('owner')
            if owner:
                queryset = queryset.filter(owner__icontains=owner)

            # Filter by deadline range
            deadline_before = request.query_params.get('deadline_before')
            if deadline_before:
                queryset = queryset.filter(deadline__lte=deadline_before)

            deadline_after = request.query_params.get('deadline_after')
            if deadline_after:
                queryset = queryset.filter(deadline__gte=deadline_after)

            # Search in content
            search = request.query_params.get('search')
            if search:
                queryset = queryset.filter(content__icontains=search)

            # Ordering
            ordering = request.query_params.get('ordering', '-created_at')
            if ordering:
                queryset = queryset.order_by(ordering)

            # Pagination
            page_size = min(
                int(request.query_params.get('page_size', 20)), 100
            )
            page = int(request.query_params.get('page', 1))

            start = (page - 1) * page_size
            end = start + page_size

            total = queryset.count()
            items = queryset[start:end]

            serializer = EmailTodoListSerializer(
                items, many=True, context={'request': request}
            )

            response_data = {
                'code': 200,
                'message': 'TODOs retrieved successfully',
                'data': {
                    'list': serializer.data,
                    'pagination': {
                        'total': total,
                        'page': page,
                        'pageSize': page_size,
                        'next': (
                            f"?page={page + 1}&page_size={page_size}"
                            if end < total else None
                        ),
                        'previous': (
                            f"?page={page - 1}&page_size={page_size}"
                            if page > 1 else None
                        )
                    }
                }
            }

            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error listing TODOs: {str(e)}")
            return Response({
                'code': 500,
                'message': 'Failed to retrieve TODOs',
                'data': None
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @extend_schema(
        operation_id='todos_create',
        summary='Create TODO',
        description='Create a new TODO item',
        request=EmailTodoSerializer,
        responses={
            201: response(EmailTodoSerializer),
            400: error_response(),
            401: error_response()
        }
    )
    def post(self, request):
        """
        Create a new TODO item
        """
        try:
            serializer = EmailTodoSerializer(
                data=request.data, context={'request': request}
            )

            if serializer.is_valid():
                todo = serializer.save()
                response_serializer = EmailTodoSerializer(
                    todo, context={'request': request}
                )

                return Response({
                    'code': 201,
                    'message': 'TODO created successfully',
                    'data': response_serializer.data
                }, status=status.HTTP_201_CREATED)

            return Response({
                'code': 400,
                'message': 'Validation failed',
                'data': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.error(f"Error creating TODO: {str(e)}")
            return Response({
                'code': 500,
                'message': 'Failed to create TODO',
                'data': None
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class EmailTodoDetailAPIView(BaseAPIView):
    """
    APIView for individual EmailTodo operations
    """

    def get_queryset(self):
        """
        Get EmailTodo queryset with related objects
        """
        return EmailTodo.objects.select_related(
            'user', 'email_message'
        ).all()

    @extend_schema(
        operation_id='todos_retrieve',
        summary='Get TODO details',
        description='Get details of a specific TODO by ID',
        responses={
            200: response(EmailTodoSerializer),
            404: error_response(),
            401: error_response()
        }
    )
    def get(self, request, pk):
        """
        Retrieve a specific TODO by ID
        """
        try:
            todo = self.get_object(pk)
            serializer = EmailTodoSerializer(
                todo, context={'request': request}
            )

            return Response({
                'code': 200,
                'message': 'TODO retrieved successfully',
                'data': serializer.data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error retrieving TODO {pk}: {str(e)}")
            return Response({
                'code': 404,
                'message': 'TODO not found',
                'data': None
            }, status=status.HTTP_404_NOT_FOUND)

    @extend_schema(
        operation_id='todos_update',
        summary='Update TODO',
        description='Update a specific TODO',
        request=EmailTodoSerializer,
        responses={
            200: response(EmailTodoSerializer),
            400: error_response(),
            404: error_response(),
            401: error_response()
        }
    )
    def patch(self, request, pk):
        """
        Update a specific TODO
        """
        try:
            todo = self.get_object(pk)
            serializer = EmailTodoSerializer(
                todo, data=request.data, partial=True,
                context={'request': request}
            )

            if serializer.is_valid():
                updated_todo = serializer.save()
                response_serializer = EmailTodoSerializer(
                    updated_todo, context={'request': request}
                )

                return Response({
                    'code': 200,
                    'message': 'TODO updated successfully',
                    'data': response_serializer.data
                }, status=status.HTTP_200_OK)

            return Response({
                'code': 400,
                'message': 'Validation failed',
                'data': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.error(f"Error updating TODO {pk}: {str(e)}")
            return Response({
                'code': 404,
                'message': 'TODO not found',
                'data': None
            }, status=status.HTTP_404_NOT_FOUND)

    @extend_schema(
        operation_id='todos_delete',
        summary='Delete TODO',
        description='Delete a specific TODO',
        responses={
            200: response(serializers.Serializer),
            404: error_response(),
            401: error_response()
        }
    )
    def delete(self, request, pk):
        """
        Delete a specific TODO
        """
        try:
            todo = self.get_object(pk)
            todo.delete()

            return Response({
                'code': 200,
                'message': 'TODO deleted successfully',
                'data': None
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error deleting TODO {pk}: {str(e)}")
            return Response({
                'code': 404,
                'message': 'TODO not found',
                'data': None
            }, status=status.HTTP_404_NOT_FOUND)


class EmailTodoStatsAPIView(BaseAPIView):
    """
    APIView for TODO statistics
    """

    def get_queryset(self):
        """
        Get EmailTodo queryset
        """
        return EmailTodo.objects.all()

    @extend_schema(
        operation_id='todos_stats',
        summary='Get TODO statistics',
        description='Get statistics about user TODOs',
        responses={
            200: response(serializers.Serializer),
            401: error_response()
        }
    )
    def get(self, request):
        """
        Get TODO statistics for the current user
        """
        try:
            queryset = self.filter_by_user(self.get_queryset())

            total = queryset.count()
            completed = queryset.filter(is_completed=True).count()
            incomplete = total - completed
            completion_rate = (
                (completed / total * 100) if total > 0 else 0.0
            )

            # Statistics by priority
            by_priority = queryset.values('priority').annotate(
                count=Count('id')
            )
            priority_stats = {'high': 0, 'medium': 0, 'low': 0, None: 0}
            for item in by_priority:
                priority = item['priority']
                if priority in priority_stats:
                    priority_stats[priority] = item['count']
                else:
                    priority_stats[None] += item['count']

            stats = {
                'total': total,
                'completed': completed,
                'incomplete': incomplete,
                'completion_rate': round(completion_rate, 2),
                'by_priority': {
                    'high': priority_stats.get('high', 0),
                    'medium': priority_stats.get('medium', 0),
                    'low': priority_stats.get('low', 0),
                    'none': priority_stats.get(None, 0)
                }
            }

            return Response({
                'code': 200,
                'message': 'Statistics retrieved successfully',
                'data': stats
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error retrieving TODO statistics: {str(e)}")
            return Response({
                'code': 500,
                'message': 'Failed to retrieve statistics',
                'data': None
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class EmailTodoBatchAPIView(BaseAPIView):
    """
    APIView for batch TODO operations
    """

    def get_queryset(self):
        """
        Get EmailTodo queryset
        """
        return EmailTodo.objects.all()

    @extend_schema(
        operation_id='todos_batch_complete',
        summary='Batch mark TODOs as completed',
        description='Mark multiple TODOs as completed',
        request={
            'type': 'object',
            'properties': {
                'todo_ids': {
                    'type': 'array',
                    'items': {'type': 'integer'}
                }
            }
        },
        responses={
            200: response(serializers.Serializer),
            400: error_response(),
            401: error_response()
        }
    )
    def post(self, request):
        """
        Batch mark TODOs as completed
        """
        try:
            todo_ids = request.data.get('todo_ids', [])
            if not todo_ids:
                return Response({
                    'code': 400,
                    'message': 'todo_ids is required',
                    'data': None
                }, status=status.HTTP_400_BAD_REQUEST)

            queryset = self.filter_by_user(self.get_queryset())
            todos = queryset.filter(id__in=todo_ids)

            completed_count = 0
            for todo in todos:
                if not todo.is_completed:
                    todo.mark_completed()
                    completed_count += 1

            return Response({
                'code': 200,
                'message': f'{completed_count} TODOs marked as completed',
                'data': {'completed_count': completed_count}
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error batch completing TODOs: {str(e)}")
            return Response({
                'code': 500,
                'message': 'Failed to batch complete TODOs',
                'data': None
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
