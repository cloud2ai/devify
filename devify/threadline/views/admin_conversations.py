"""
Admin-only conversation management views.
"""

from __future__ import annotations

from datetime import datetime, time as dt_time

from django.db.models import Count, Q
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from core.swagger import error_response, pagination_response, response
from agentcore_task.adapters.django.models import TaskExecution
from agentcore_task.adapters.django.serializers import (
    TaskExecutionSerializer,
)
from threadline.models import EmailMessage
from threadline.serializers import (
    AdminConversationListSerializer,
    AdminConversationTaskListSerializer,
    EmailMessageSerializer,
)


def _apply_date_boundaries(queryset, start_date=None, end_date=None):
    if start_date:
        parsed = parse_datetime(start_date)
        if parsed is None:
            parsed_date = parse_date(start_date)
            if parsed_date:
                parsed = datetime.combine(parsed_date, dt_time.min)
                if timezone.is_naive(parsed):
                    parsed = timezone.make_aware(
                        parsed, timezone.get_current_timezone()
                    )
        if parsed:
            queryset = queryset.filter(received_at__gte=parsed)
    if end_date:
        parsed = parse_datetime(end_date)
        if parsed is None:
            parsed_date = parse_date(end_date)
            if parsed_date:
                parsed = datetime.combine(parsed_date, dt_time.max)
                if timezone.is_naive(parsed):
                    parsed = timezone.make_aware(
                        parsed, timezone.get_current_timezone()
                    )
        if parsed:
            queryset = queryset.filter(received_at__lte=parsed)
    return queryset


def _get_conversation(uuid):
    """Fetch an EmailMessage by UUID with user and merge-target joins."""
    return (
        EmailMessage.objects.select_related("user", "merged_into")
        .filter(uuid=uuid)
        .first()
    )


def _apply_email_filters(queryset, conversation):
    """Filter task executions linked to a conversation via metadata context."""
    email_filters = Q(metadata__context__email_id=str(conversation.id))
    email_filters |= Q(metadata__context__email_id=conversation.id)
    return queryset.filter(email_filters)


class AdminConversationListAPIView(APIView):
    """
    Read-only admin list for threadline conversations.
    """

    permission_classes = [IsAdminUser]

    def get_queryset(self):
        return (
            EmailMessage.objects.select_related("user", "merged_into")
            .annotate(
                relay_delivery_count=Count("relay_events__deliveries"),
            )
            .order_by("-received_at", "-id")
        )

    @extend_schema(
        operation_id="admin_threadline_conversations_list",
        summary="List admin threadline conversations",
        description="List all threadline messages with user and relay context.",
        responses={
            200: pagination_response(AdminConversationListSerializer),
            401: error_response(),
            403: error_response(),
        },
    )
    def get(self, request):
        queryset = self.get_queryset()

        search = (request.query_params.get("search") or "").strip()
        if search:
            for keyword in [part for part in search.replace(",", " ").split() if part]:
                queryset = queryset.filter(
                    Q(subject__icontains=keyword)
                    | Q(sender__icontains=keyword)
                    | Q(recipients__icontains=keyword)
                    | Q(summary_title__icontains=keyword)
                    | Q(summary_content__icontains=keyword)
                    | Q(llm_content__icontains=keyword)
                    | Q(text_content__icontains=keyword)
                    | Q(message_id__icontains=keyword)
                )

        status_value = (request.query_params.get("status") or "").strip()
        if status_value:
            queryset = queryset.filter(status=status_value)

        user_id = (request.query_params.get("user_id") or "").strip()
        if user_id:
            queryset = queryset.filter(user_id=user_id)

        queryset = _apply_date_boundaries(
            queryset,
            start_date=request.query_params.get("start_date"),
            end_date=request.query_params.get("end_date"),
        )

        ordering = (request.query_params.get("ordering") or "-received_at").strip()
        allowed_ordering = {
            "received_at",
            "-received_at",
            "created_at",
            "-created_at",
            "subject",
            "-subject",
            "status",
            "-status",
        }
        if ordering not in allowed_ordering:
            ordering = "-received_at"
        queryset = queryset.order_by(ordering, "-id")

        try:
            page_size = min(int(request.query_params.get("page_size", 20)), 100)
        except (TypeError, ValueError):
            page_size = 20
        try:
            page = max(int(request.query_params.get("page", 1)), 1)
        except (TypeError, ValueError):
            page = 1

        total = queryset.count()
        start = (page - 1) * page_size
        end = start + page_size
        items = queryset[start:end]

        serializer = AdminConversationListSerializer(
            items,
            many=True,
            context={"request": request},
        )
        return Response(
            {
                "code": 200,
                "message": "Threadline conversations retrieved successfully",
                "data": {
                    "list": serializer.data,
                    "pagination": {
                        "total": total,
                        "page": page,
                        "pageSize": page_size,
                        "next": (
                            f"?page={page + 1}&page_size={page_size}"
                            if end < total
                            else None
                        ),
                        "previous": (
                            f"?page={page - 1}&page_size={page_size}"
                            if page > 1
                            else None
                        ),
                    },
                },
            }
        )


class AdminConversationDetailAPIView(APIView):
    """
    Read-only admin detail for a single threadline conversation.
    """

    permission_classes = [IsAdminUser]

    def get_queryset(self):
        return (
            EmailMessage.objects.select_related("user", "merged_into")
            .prefetch_related("attachments")
            .prefetch_related("todos")
            .prefetch_related("merged_children")
            .prefetch_related("issues")
            .prefetch_related("share_links")
            .prefetch_related("relay_events")
            .prefetch_related("relay_events__deliveries")
            .prefetch_related("relay_events__deliveries__subscription")
        )

    @extend_schema(
        operation_id="admin_threadline_conversation_detail",
        summary="Retrieve admin threadline conversation",
        description="Get the full details for one threadline message.",
        responses={
            200: response(EmailMessageSerializer),
            401: error_response(),
            403: error_response(),
            404: error_response(),
        },
    )
    def get(self, request, uuid):
        message = (
            self.get_queryset()
            .filter(uuid=uuid)
            .first()
        )
        if not message:
            return Response(
                {"code": 404, "message": "Conversation not found", "data": None},
                status=404,
            )
        serializer = EmailMessageSerializer(
            message,
            context={"request": request},
        )
        return Response(
            {
                "code": 200,
                "message": "Threadline conversation retrieved successfully",
                "data": serializer.data,
            }
        )


class AdminConversationTasksAPIView(APIView):
    """
    Read-only admin list for task executions linked to a conversation.
    """

    permission_classes = [IsAdminUser]

    def get_queryset(self):
        return TaskExecution.objects.select_related("created_by").all()

    @extend_schema(
        operation_id="admin_threadline_conversation_tasks_list",
        summary="List admin task executions for conversation",
        description="List task executions related to one threadline message.",
        responses={
            200: pagination_response(AdminConversationTaskListSerializer),
            401: error_response(),
            403: error_response(),
            404: error_response(),
        },
    )
    def get(self, request, uuid):
        conversation = _get_conversation(uuid)
        if not conversation:
            return Response(
                {"code": 404, "message": "Conversation not found", "data": None},
                status=404,
            )

        queryset = (
            _apply_email_filters(self.get_queryset(), conversation)
            .defer(
                "task_args",
                "task_kwargs",
                "result",
                "error",
                "traceback",
                "metadata",
            )
        )
        queryset = queryset.order_by("-created_at", "-id")

        try:
            page_size = min(int(request.query_params.get("page_size", 20)), 100)
        except (TypeError, ValueError):
            page_size = 20
        try:
            page = max(int(request.query_params.get("page", 1)), 1)
        except (TypeError, ValueError):
            page = 1

        total = queryset.count()
        start = (page - 1) * page_size
        end = start + page_size
        items = queryset[start:end]

        serializer = AdminConversationTaskListSerializer(
            items,
            many=True,
            context={"request": request},
        )
        return Response(
            {
                "code": 200,
                "message": "Conversation task executions retrieved successfully",
                "data": {
                    "list": serializer.data,
                    "pagination": {
                        "total": total,
                        "page": page,
                        "pageSize": page_size,
                        "next": (
                            f"?page={page + 1}&page_size={page_size}"
                            if end < total
                            else None
                        ),
                        "previous": (
                            f"?page={page - 1}&page_size={page_size}"
                            if page > 1
                            else None
                        ),
                    },
                },
            }
        )


class AdminConversationTaskDetailAPIView(APIView):
    """
    Read-only admin detail for a conversation-linked task execution.
    """

    permission_classes = [IsAdminUser]

    def get_queryset(self):
        return TaskExecution.objects.select_related("created_by").all()

    @extend_schema(
        operation_id="admin_threadline_conversation_task_detail",
        summary="Retrieve admin task execution for conversation",
        description="Get the full task execution details for one task linked to a threadline message.",
        responses={
            200: response(TaskExecutionSerializer),
            401: error_response(),
            403: error_response(),
            404: error_response(),
        },
    )
    def get(self, request, uuid, task_pk):
        conversation = _get_conversation(uuid)
        if not conversation:
            return Response(
                {"code": 404, "message": "Conversation not found", "data": None},
                status=404,
            )

        task = (
            _apply_email_filters(self.get_queryset(), conversation)
            .filter(pk=task_pk)
            .first()
        )
        if not task:
            return Response(
                {"code": 404, "message": "Task not found", "data": None},
                status=404,
            )

        serializer = TaskExecutionSerializer(
            task,
            context={"request": request},
        )
        return Response(
            {
                "code": 200,
                "message": "Conversation task execution retrieved successfully",
                "data": serializer.data,
            }
        )
