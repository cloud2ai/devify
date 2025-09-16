"""
Issue API Views

This module contains APIView classes for Issue model CRUD operations.
Note: These views are not exposed in the public API.
"""

import logging
from rest_framework import status, serializers
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from core.swagger import response, error_response, pagination_response

from .base import BaseAPIView
from ..models import Issue
from ..serializers import (
    IssueSerializer,
    IssueCreateSerializer,
    IssueUpdateSerializer
)

logger = logging.getLogger(__name__)


class IssueAPIView(BaseAPIView):
    """
    APIView for Issue CRUD operations
    Note: This view is not exposed in the public API.
    """

    def get_queryset(self):
        """
        Get Issue queryset with related objects
        """
        return Issue.objects.select_related('email_message', 'user').all()

    @extend_schema(
        operation_id='issues_list',
        summary='List issues',
        description='Get paginated list of user issues',
        parameters=[
            OpenApiParameter(
                name='search',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Search in title, description fields'
            ),
            OpenApiParameter(
                name='engine',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Filter by engine type'
            ),
            OpenApiParameter(
                name='priority',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Filter by priority level'
            ),
            OpenApiParameter(
                name='email_message_id',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Filter by email message ID'
            ),
            OpenApiParameter(
                name='ordering',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Order by field (e.g., priority, created_at)'
            )
        ],
        responses={
            200: pagination_response(IssueSerializer),
            401: error_response()
        }
    )
    def get(self, request):
        """
        List user issues with pagination and filtering
        """
        try:
            queryset = self.filter_by_user(self.get_queryset())

            # Search functionality
            search = request.query_params.get('search', None)
            if search:
                queryset = queryset.filter(
                    Q(title__icontains=search) |
                    Q(description__icontains=search)
                )

            # Filter by engine
            engine = request.query_params.get('engine', None)
            if engine:
                queryset = queryset.filter(engine=engine)

            # Filter by priority
            priority = request.query_params.get('priority', None)
            if priority:
                queryset = queryset.filter(priority=priority)

            # Filter by email message
            email_message_id = request.query_params.get('email_message_id', None)
            if email_message_id:
                queryset = queryset.filter(email_message_id=email_message_id)

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

            serializer = IssueSerializer(items, many=True, context={'request': request})

            response_data = {
                'code': 200,
                'message': 'Issues retrieved successfully',
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
            logger.error(f"Error listing issues: {str(e)}")
            return Response({
                'code': 500,
                'message': 'Internal server error',
                'data': None
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @extend_schema(
        operation_id='issues_create',
        summary='Create new issue',
        description='Create a new issue',
        request=IssueCreateSerializer,
        responses={
            201: response(IssueSerializer),
            400: error_response(),
            401: error_response()
        }
    )
    def post(self, request):
        """
        Create a new issue
        """
        try:
            serializer = IssueCreateSerializer(
                data=request.data,
                context={'request': request}
            )

            if serializer.is_valid(raise_exception=True):
                issue = serializer.save()
                response_serializer = IssueSerializer(issue, context={'request': request})

                return Response({
                    'code': 201,
                    'message': 'Issue created successfully',
                    'data': response_serializer.data
                }, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"Error creating issue: {str(e)}")
            return Response({
                'code': 400,
                'message': str(e),
                'data': None
            }, status=status.HTTP_400_BAD_REQUEST)


class IssueDetailAPIView(BaseAPIView):
    """
    APIView for individual Issue operations
    Note: This view is not exposed in the public API.
    """

    def get_queryset(self):
        """
        Get Issue queryset with related objects
        """
        return Issue.objects.select_related('email_message', 'user').all()

    @extend_schema(
        operation_id='issues_retrieve',
        summary='Get issue details',
        description='Get details of a specific issue',
        responses={
            200: response(IssueSerializer),
            404: error_response(),
            401: error_response()
        }
    )
    def get(self, request, pk):
        """
        Retrieve a specific issue
        """
        try:
            issue = self.get_object(pk)
            serializer = IssueSerializer(issue, context={'request': request})

            return Response({
                'code': 200,
                'message': 'Issue retrieved successfully',
                'data': serializer.data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error retrieving issue {pk}: {str(e)}")
            return Response({
                'code': 404,
                'message': 'Issue not found',
                'data': None
            }, status=status.HTTP_404_NOT_FOUND)

    @extend_schema(
        operation_id='issues_update',
        summary='Update issue',
        description='Update a specific issue',
        request=IssueUpdateSerializer,
        responses={
            200: response(IssueSerializer),
            400: error_response(),
            404: error_response(),
            401: error_response()
        }
    )
    def put(self, request, pk):
        """
        Update a specific issue (full update)
        """
        try:
            issue = self.get_object(pk)
            serializer = IssueUpdateSerializer(
                issue,
                data=request.data,
                context={'request': request}
            )

            if serializer.is_valid(raise_exception=True):
                updated_issue = serializer.save()
                response_serializer = IssueSerializer(updated_issue, context={'request': request})

                return Response({
                    'code': 200,
                    'message': 'Issue updated successfully',
                    'data': response_serializer.data
                }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error updating issue {pk}: {str(e)}")
            return Response({
                'code': 400,
                'message': str(e),
                'data': None
            }, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        operation_id='issues_partial_update',
        summary='Partially update issue',
        description='Partially update a specific issue',
        request=IssueUpdateSerializer,
        responses={
            200: response(IssueSerializer),
            400: error_response(),
            404: error_response(),
            401: error_response()
        }
    )
    def patch(self, request, pk):
        """
        Partially update a specific issue
        """
        try:
            issue = self.get_object(pk)
            serializer = IssueUpdateSerializer(
                issue,
                data=request.data,
                partial=True,
                context={'request': request}
            )

            if serializer.is_valid(raise_exception=True):
                updated_issue = serializer.save()
                response_serializer = IssueSerializer(updated_issue, context={'request': request})

                return Response({
                    'code': 200,
                    'message': 'Issue updated successfully',
                    'data': response_serializer.data
                }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error updating issue {pk}: {str(e)}")
            return Response({
                'code': 400,
                'message': str(e),
                'data': None
            }, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        operation_id='issues_delete',
        summary='Delete issue',
        description='Delete a specific issue',
        responses={
            204: error_response(),
            404: error_response(),
            401: error_response()
        }
    )
    def delete(self, request, pk):
        """
        Delete a specific issue
        """
        try:
            issue = self.get_object(pk)
            issue.delete()

            return Response({
                'code': 204,
                'message': 'Issue deleted successfully',
                'data': None
            }, status=status.HTTP_204_NO_CONTENT)

        except Exception as e:
            logger.error(f"Error deleting issue {pk}: {str(e)}")
            return Response({
                'code': 404,
                'message': 'Issue not found',
                'data': None
            }, status=status.HTTP_404_NOT_FOUND)
