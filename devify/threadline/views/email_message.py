"""
EmailMessage API Views

This module contains APIView classes for EmailMessage model CRUD operations.
"""

import logging
import re

from django.utils.translation import gettext_lazy as _
from rest_framework import status, serializers
from rest_framework.response import Response
from django.db.models import Q
from django.db import transaction
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from core.swagger import response, error_response, pagination_response

from .base import BaseAPIView
from ..models import EmailMessage
from ..serializers import (
    EmailMessageSerializer,
    EmailMessageListSerializer,
    EmailMessageCreateSerializer,
    EmailMessageUpdateSerializer,
    EmailMessageMergeSerializer,
    EmailMessageBatchRetrySerializer,
)
from ..services import (
    ManualMergeService,
    enqueue_merge_workflow as _enqueue_merge_workflow,
    enqueue_merge_workflows as _enqueue_merge_workflows,
)

logger = logging.getLogger(__name__)


def _serialize_issue_cluster(message: EmailMessage) -> dict:
    """
    Serialize the merge cluster for on-demand issue inspection.
    """
    visited: set[int] = set()
    nodes: list[dict] = []

    def get_direct_issue(obj: EmailMessage):
        cache = getattr(obj, "_prefetched_objects_cache", None)
        if cache and "issues" in cache:
            prefetched = cache["issues"]
            if prefetched:
                return prefetched[0]
            return None

        return obj.issues.order_by("-created_at", "-id").first()

    def walk(obj: EmailMessage, depth: int = 0):
        if not obj or obj.id in visited:
            return
        visited.add(obj.id)

        issue = get_direct_issue(obj)
        nodes.append(
            {
                "email_id": obj.id,
                "email_uuid": str(obj.uuid),
                "subject": obj.subject,
                "merged_into_id": obj.merged_into_id,
                "merged_into_uuid": (
                    str(obj.merged_into.uuid)
                    if obj.merged_into_id and obj.merged_into
                    else None
                ),
                "depth": depth,
                "has_issue": bool(issue),
                "issue_id": issue.id if issue else None,
                "issue_external_id": issue.external_id if issue else None,
                "issue_url": issue.issue_url if issue else None,
            }
        )

        if obj.merged_into_id and obj.merged_into:
            walk(obj.merged_into, depth + 1)

        for child in obj.merged_children.all():
            walk(child, depth + 1)

    walk(message)

    return {
        "root": {
            "email_id": message.id,
            "email_uuid": str(message.uuid),
            "subject": message.subject,
            "merged_into_id": message.merged_into_id,
            "merged_into_uuid": (
                str(message.merged_into.uuid)
                if message.merged_into_id and message.merged_into
                else None
            ),
        },
        "nodes": nodes,
        "issue_count": sum(1 for node in nodes if node["has_issue"]),
        "node_count": len(nodes),
    }


def _serialize_merge_response(message: EmailMessage, request, result):
    serializer = EmailMessageSerializer(message, context={"request": request})
    return {
        "threadline": serializer.data,
        "source_count": len(result.source_messages),
        "attachment_count": result.attachment_count,
        "source_uuids": [str(item.uuid) for item in result.source_messages],
    }


class EmailMessageAPIView(BaseAPIView):
    """
    APIView for EmailMessage CRUD operations
    """

    def get_queryset(self):
        """
        Get EmailMessage queryset with related objects
        """
        return (
            EmailMessage.objects.select_related("user", "merged_into")
            .prefetch_related("merged_children")
            .prefetch_related("issues")
            .prefetch_related("share_links")
            .filter(merged_into__isnull=True)
            .all()
        )

    @extend_schema(
        operation_id="threadlines_list",
        summary="List threadlines",
        description=(
            "Get paginated list of user threadlines "
            "(email messages with attachments)"
        ),
        parameters=[
            OpenApiParameter(
                name="search",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Search in subject, sender, recipients fields",
            ),
            OpenApiParameter(
                name="status",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Filter by processing status",
            ),
            OpenApiParameter(
                name="ordering",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Order by field (e.g., received_at, created_at)",
            ),
        ],
        responses={
            200: pagination_response(EmailMessageListSerializer),
            401: error_response(),
        },
    )
    def get(self, request):
        """
        List user threadlines with pagination and filtering
        """
        try:
            # Set request for base class methods
            self.request = request
            queryset = self.filter_by_user(self.get_queryset())

            # Enhanced search functionality with multi-keyword AND logic
            search = request.query_params.get("search", None)
            if search:
                # Parse multiple keywords from search query
                # Support space or comma separated keywords
                # This will split "lizengyuan project" into
                # ["lizengyuan", "project"]
                # But keep "lizengyuan" as a single keyword
                keywords = [
                    k.strip() for k in re.split(r"[,\s]+", search) if k.strip()
                ]

                logger.info(f"Search query parsed into keywords: {keywords}")

                if keywords:
                # Build AND logic: each keyword must match at least one field.
                    for keyword in keywords:
                        logger.debug(f"Filtering by keyword: '{keyword}'")
                        queryset = queryset.filter(
                            Q(subject__icontains=keyword)
                            | Q(sender__icontains=keyword)
                            | Q(recipients__icontains=keyword)
                            | Q(summary_title__icontains=keyword)
                            | Q(summary_content__icontains=keyword)
                            | Q(llm_content__icontains=keyword)
                            | Q(text_content__icontains=keyword)
                        )

            # Filter by status
            message_status = request.query_params.get("status", None)
            if message_status:
                queryset = queryset.filter(status=message_status)

            # Ordering
            ordering = request.query_params.get("ordering", "-received_at")
            if ordering:
                queryset = queryset.order_by(ordering)

            # Pagination
            page_size = min(
                int(request.query_params.get("page_size", 10)), 100
            )
            page = int(request.query_params.get("page", 1))

            start = (page - 1) * page_size
            end = start + page_size

            total = queryset.count()
            items = queryset[start:end]

            serializer = EmailMessageListSerializer(
                items, many=True, context={"request": request}
            )

            response_data = {
                "code": 200,
                "message": "Threadlines retrieved successfully",
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

            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error listing email messages: {str(e)}")
            return Response(
                {
                    "code": 500,
                    "message": "Internal server error",
                    "data": None,
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @extend_schema(
        operation_id="threadlines_create",
        summary="Create new threadline",
        description="Create a new threadline (email message with attachments)",
        request=EmailMessageCreateSerializer,
        responses={
            201: response(EmailMessageSerializer),
            400: error_response(),
            401: error_response(),
        },
    )
    def post(self, request):
        """
        Create a new threadline
        """
        try:
            # Set request for base class methods
            self.request = request
            serializer = EmailMessageCreateSerializer(
                data=request.data, context={"request": request}
            )

            if serializer.is_valid(raise_exception=True):
                message = serializer.save()
                try:
                    _enqueue_merge_workflow(message)
                    logger.info(
                        f"Triggered merge workflow for newly created "
                        f"threadline {message.id}"
                    )
                except Exception as workflow_error:
                    logger.error(
                        f"Failed to trigger workflow for threadline "
                        f"{message.id}: {workflow_error}"
                    )
                    return Response(
                        {
                            "code": 503,
                            "message": str(workflow_error),
                            "data": EmailMessageSerializer(
                                message, context={"request": request}
                            ).data,
                        },
                        status=status.HTTP_503_SERVICE_UNAVAILABLE,
                    )

                response_serializer = EmailMessageSerializer(
                    message, context={"request": request}
                )

                return Response(
                    {
                        "code": 201,
                        "message": "Threadline created successfully",
                        "data": response_serializer.data,
                    },
                    status=status.HTTP_201_CREATED,
                )

        except Exception as e:
            logger.error(f"Error creating email message: {str(e)}")
            return Response(
                {"code": 400, "message": str(e), "data": None},
                status=status.HTTP_400_BAD_REQUEST,
            )


class EmailMessageBatchMergeAPIView(BaseAPIView):
    """
    APIView for manual batch merge operations.
    """

    def get_queryset(self):
        return (
            EmailMessage.objects.select_related("user", "merged_into")
            .prefetch_related("attachments")
            .all()
        )

    @extend_schema(
        operation_id="threadlines_merge",
        summary="Manually merge threadlines",
        description="Merge 2 to 5 threadlines into a new canonical record",
        request=EmailMessageMergeSerializer,
        responses={
            201: response(EmailMessageSerializer),
            400: error_response(),
            401: error_response(),
        },
    )
    def post(self, request):
        try:
            self.request = request
            serializer = EmailMessageMergeSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            source_uuids = serializer.validated_data["source_uuids"]
            with transaction.atomic():
                queryset = self.filter_by_user(self.get_queryset())
                source_messages = list(
                    queryset.select_for_update()
                    .filter(uuid__in=source_uuids)
                    .order_by("received_at", "id")
                )

                if len(source_messages) != len(source_uuids):
                    found_uuids = {
                        str(message.uuid) for message in source_messages
                    }
                    missing = [
                        str(uuid)
                        for uuid in source_uuids
                        if str(uuid) not in found_uuids
                    ]
                    raise serializers.ValidationError(
                        {
                            "source_uuids": [
                                "One or more selected messages were not "
                                "found or are not accessible"
                            ],
                            "missing_source_uuids": missing,
                        }
                    )

                if any(message.merged_into_id for message in source_messages):
                    raise serializers.ValidationError(
                        {
                            "source_uuids": [
                                "Merged child messages cannot be merged again"
                            ]
                        }
                    )

                merge_service = ManualMergeService()
                result = merge_service.merge(
                    user=request.user,
                    source_messages=source_messages,
                    merge_note=serializer.validated_data.get("merge_note"),
                )

            try:
                _enqueue_merge_workflow(result.canonical_message)
            except Exception as workflow_error:
                logger.warning(
                    "Failed to trigger workflow for manual merge %s: %s",
                    result.canonical_message.uuid,
                    workflow_error,
                )
                return Response(
                    {
                        "code": 201,
                        "message": (
                            "Threadlines merged successfully, but "
                            "workflow dispatch failed"
                        ),
                        "data": _serialize_merge_response(
                            result.canonical_message,
                            request,
                            result,
                        ),
                        "workflow_dispatched": False,
                        "workflow_error": str(workflow_error),
                    },
                    status=status.HTTP_201_CREATED,
                )

            return Response(
                {
                    "code": 201,
                    "message": "Threadlines merged successfully",
                    "data": _serialize_merge_response(
                        result.canonical_message,
                        request,
                        result,
                    ),
                },
                status=status.HTTP_201_CREATED,
            )

        except serializers.ValidationError as exc:
            return Response(
                {
                    "code": 400,
                    "message": "Validation failed",
                    "data": exc.detail,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as exc:
            logger.error(f"Error merging email messages: {exc}")
            return Response(
                {"code": 500, "message": str(exc), "data": None},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class EmailMessageBatchRetryAPIView(BaseAPIView):
    """
    APIView for batch retry operations.
    """

    lookup_field = "uuid"

    def get_queryset(self):
        return (
            EmailMessage.objects.select_related("user", "merged_into")
            .prefetch_related("merged_children")
            .prefetch_related("issues")
            .prefetch_related("share_links")
            .all()
        )

    @extend_schema(
        operation_id="threadlines_batch_retry",
        summary="Batch retry email processing",
        description=(
            "Retry processing for multiple threadlines with optional "
            "language and scene override"
        ),
        request=EmailMessageBatchRetrySerializer,
        responses={
            200: response(serializers.DictField),
            400: error_response(),
            401: error_response(),
        },
    )
    def post(self, request):
        """
        Retry processing for multiple threadlines.
        """
        try:
            self.request = request
            serializer = EmailMessageBatchRetrySerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            source_uuids = serializer.validated_data["source_uuids"]
            language = serializer.validated_data.get("language")
            scene = serializer.validated_data.get("scene")
            force = serializer.validated_data.get("force", False)

            queryset = self.filter_by_user(self.get_queryset())
            messages = list(
                queryset.filter(uuid__in=source_uuids).order_by("id")
            )

            if len(messages) != len(source_uuids):
                found_uuids = {str(message.uuid) for message in messages}
                missing = [
                    str(uuid)
                    for uuid in source_uuids
                    if str(uuid) not in found_uuids
                ]
                raise serializers.ValidationError(
                    {
                        "source_uuids": [
                            "One or more selected messages were not "
                            "found or are not accessible"
                        ],
                        "missing_source_uuids": missing,
                    }
                )

            results = _enqueue_merge_workflows(
                messages,
                force=force,
                language=language,
                scene=scene,
                trigger_source="api_batch_retry",
            )

            success_count = sum(
                1 for item in results if item.get("status") == "success"
            )
            failure_count = len(results) - success_count
            if failure_count == 0:
                message_text = _("Batch retry triggered successfully")
                response_status = status.HTTP_200_OK
            elif success_count == 0:
                message_text = _("Batch retry failed")
                response_status = status.HTTP_503_SERVICE_UNAVAILABLE
            else:
                message_text = _(
                    "Batch retry triggered with partial failures"
                )
                response_status = status.HTTP_200_OK

            return Response(
                {
                    "code": response_status,
                    "message": message_text,
                    "data": {
                        "results": results,
                        "success_count": success_count,
                        "failure_count": failure_count,
                    },
                },
                status=response_status,
            )

        except serializers.ValidationError as exc:
            return Response(
                {
                    "code": 400,
                    "message": "Validation failed",
                    "data": exc.detail,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as exc:
            logger.error(f"Error batch retrying email messages: {exc}")
            return Response(
                {"code": 500, "message": str(exc), "data": None},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class EmailMessageDetailAPIView(BaseAPIView):
    """
    APIView for individual EmailMessage operations
    """

    lookup_field = "uuid"

    def get_queryset(self):
        """
        Get EmailMessage queryset with related objects
        """
        return (
            EmailMessage.objects.select_related("user", "merged_into")
            .prefetch_related("merged_children")
            .prefetch_related("issues")
            .prefetch_related("share_links")
            .all()
        )

    def get_object(self, uuid):
        """
        Get email message by UUID with user ownership validation
        """
        return self.get_queryset().get(uuid=uuid, user=self.request.user)

    @extend_schema(
        operation_id="threadlines_retrieve",
        summary="Get threadline details",
        description="Get details of a specific threadline by UUID",
        responses={
            200: response(EmailMessageSerializer),
            404: error_response(),
            401: error_response(),
        },
    )
    def get(self, request, uuid):
        """
        Retrieve a specific threadline by UUID
        """
        try:
            message = self.get_object(uuid)
            serializer = EmailMessageSerializer(
                message, context={"request": request}
            )

            return Response(
                {
                    "code": 200,
                    "message": "Threadline retrieved successfully",
                    "data": serializer.data,
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            logger.error(f"Error retrieving threadline {uuid}: {str(e)}")
            return Response(
                {"code": 404, "message": "Threadline not found", "data": None},
                status=status.HTTP_404_NOT_FOUND,
            )

    @extend_schema(
        operation_id="threadlines_update",
        summary="Update email message",
        description="Update a specific email message",
        request=EmailMessageUpdateSerializer,
        responses={
            200: response(EmailMessageSerializer),
            400: error_response(),
            404: error_response(),
            401: error_response(),
        },
    )
    def put(self, request, uuid):
        """
        Update a specific email message (full update)
        """
        try:
            message = self.get_object(uuid)
            serializer = EmailMessageUpdateSerializer(
                message, data=request.data, context={"request": request}
            )

            if serializer.is_valid(raise_exception=True):
                updated_message = serializer.save()
                response_serializer = EmailMessageSerializer(
                    updated_message, context={"request": request}
                )

                return Response(
                    {
                        "code": 200,
                        "message": "Email message updated successfully",
                        "data": response_serializer.data,
                    },
                    status=status.HTTP_200_OK,
                )

        except Exception as e:
            logger.error(f"Error updating email message {uuid}: {str(e)}")
            return Response(
                {"code": 400, "message": str(e), "data": None},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @extend_schema(
        operation_id="email_messages_partial_update",
        summary="Partially update email message",
        description="Partially update a specific email message",
        request=EmailMessageUpdateSerializer,
        responses={
            200: response(EmailMessageSerializer),
            400: error_response(),
            404: error_response(),
            401: error_response(),
        },
    )
    def patch(self, request, uuid):
        """
        Partially update a specific email message
        """
        try:
            message = self.get_object(uuid)
            serializer = EmailMessageUpdateSerializer(
                message,
                data=request.data,
                partial=True,
                context={"request": request},
            )

            if serializer.is_valid(raise_exception=True):
                updated_message = serializer.save()
                response_serializer = EmailMessageSerializer(
                    updated_message, context={"request": request}
                )

                return Response(
                    {
                        "code": 200,
                        "message": "Email message updated successfully",
                        "data": response_serializer.data,
                    },
                    status=status.HTTP_200_OK,
                )

        except Exception as e:
            logger.error(f"Error updating email message {uuid}: {str(e)}")
            return Response(
                {"code": 400, "message": str(e), "data": None},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @extend_schema(
        operation_id="threadlines_delete",
        summary="Delete email message",
        description="Delete a specific email message",
        responses={
            204: error_response(),
            404: error_response(),
            401: error_response(),
        },
    )
    def delete(self, request, uuid):
        """
        Delete a specific email message
        """
        try:
            message = self.get_object(uuid)
            message.delete()

            return Response(
                {
                    "code": 204,
                    "message": "Email message deleted successfully",
                    "data": None,
                },
                status=status.HTTP_204_NO_CONTENT,
            )

        except Exception as e:
            logger.error(f"Error deleting email message {uuid}: {str(e)}")
            return Response(
                {
                    "code": 404,
                    "message": "Email message not found",
                    "data": None,
                },
                status=status.HTTP_404_NOT_FOUND,
            )

    @extend_schema(
        operation_id="threadlines_retry",
        summary="Retry email processing",
        description=(
            "Retry processing an email with optional language "
            "and scene override"
        ),
        request=serializers.Serializer,
        parameters=[
            OpenApiParameter(
                name="language",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Processing language (e.g., zh-CN, en-US)",
                required=False,
            ),
            OpenApiParameter(
                name="scene",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Processing scene (e.g., chat, product_issue)",
                required=False,
            ),
            OpenApiParameter(
                name="force",
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
                description=(
                    "Force retry (re-process OCR and LLM even if "
                    "already done)"
                ),
                required=False,
            ),
        ],
        responses={
            200: response(serializers.DictField),
            400: error_response(),
            404: error_response(),
            401: error_response(),
        },
    )
    def post(self, request, uuid):
        """Retry processing an email message with optional language and scene
        override.

        This endpoint allows retrying email processing with different
        language and scene settings. The force parameter determines
        whether to re-process OCR and LLM even if results already exist.
        """
        try:
            message = self.get_object(uuid)

            language = request.data.get("language") or (
                request.query_params.get("language")
            )
            scene = request.data.get("scene") or request.query_params.get(
                "scene"
            )
            force = request.data.get("force", False)
            if isinstance(force, str):
                force = force.lower() in ("true", "1", "yes")

            logger.info(
                f"Retry requested for email {uuid}, "
                f"language={language}, scene={scene}, force={force}, "
                f"trigger_source=api_retry"
            )

            target_message = _enqueue_merge_workflow(
                message,
                force=force,
                language=language,
                scene=scene,
                trigger_source="api_retry",
            )

            return Response(
                {
                    "code": 200,
                    "message": "Retry task triggered successfully",
                    "data": {
                        "email_id": str(target_message.id),
                        "uuid": str(target_message.uuid),
                        "language": language,
                        "scene": scene,
                        "force": force,
                        "requested_email_id": str(message.id),
                        "requested_uuid": str(message.uuid),
                    },
                },
                status=status.HTTP_200_OK,
            )

        except EmailMessage.DoesNotExist:
            logger.error(f"EmailMessage {uuid} not found for retry")
            return Response(
                {"code": 404, "message": "Threadline not found", "data": None},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            logger.error(f"Error triggering retry for {uuid}: {str(e)}")
            return Response(
                {"code": 503, "message": str(e), "data": None},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )


class EmailMessageIssueClusterAPIView(BaseAPIView):
    """
    APIView for on-demand issue cluster inspection.
    """

    lookup_field = "uuid"

    def get_queryset(self):
        return (
            EmailMessage.objects.select_related("user", "merged_into")
            .prefetch_related("merged_children")
            .prefetch_related("issues")
            .all()
        )

    def get_object(self, uuid):
        return self.get_queryset().get(uuid=uuid, user=self.request.user)

    @extend_schema(
        operation_id="threadlines_issue_cluster",
        summary="Get issue cluster",
        description="Get issue nodes across the merged cluster on demand",
        responses={
            200: response(serializers.DictField),
            401: error_response(),
            404: error_response(),
        },
    )
    def get(self, request, uuid):
        try:
            self.request = request
            message = self.get_object(uuid)
            return Response(
                {
                    "code": 200,
                    "message": "Issue cluster retrieved successfully",
                    "data": _serialize_issue_cluster(message),
                },
                status=status.HTTP_200_OK,
            )
        except EmailMessage.DoesNotExist:
            logger.error(f"EmailMessage with UUID {uuid} not found")
            return Response(
                {"code": 404, "message": "Threadline not found", "data": None},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            logger.error(f"Error retrieving issue cluster {uuid}: {str(e)}")
            return Response(
                {
                    "code": 500,
                    "message": "Internal server error",
                    "data": None,
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class EmailMessageMetadataAPIView(BaseAPIView):
    """
    APIView for partial updates to EmailMessage.metadata field only.

    This view supports merge-patch-like semantics for updating or creating
    metadata keys. Passing null can be used to remove a key if needed.
    """

    lookup_field = "uuid"

    def get_object(self, uuid):
        """Get email message by UUID with user ownership validation."""
        return EmailMessage.objects.get(uuid=uuid, user=self.request.user)

    @extend_schema(
        operation_id="threadlines_update_metadata",
        summary="Partially update threadline metadata",
        description=(
            "Update one or more metadata keys for a specific threadline by "
            "UUID. Only provided keys will be updated. "
            "Use null to delete a key if supported."
        ),
        request=OpenApiTypes.OBJECT,
        responses={
            200: response(EmailMessageSerializer),
            400: error_response(),
            404: error_response(),
            401: error_response(),
        },
    )
    def patch(self, request, uuid):
        """Partially update metadata dictionary for the given threadline."""
        try:
            message = self.get_object(uuid)

            if not isinstance(request.data, dict):
                return Response(
                    {
                        "code": 400,
                        "message": "Payload must be a JSON object",
                        "data": None,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            current = message.metadata or {}

            for key, value in request.data.items():
                if value is None:
                    if key in current:
                        current.pop(key)
                else:
                    current[key] = value

            message.metadata = current
            message.save(update_fields=["metadata", "updated_at"])

            return Response(
                {
                    "code": 200,
                    "message": "Metadata updated successfully",
                    "data": {
                        "uuid": str(message.uuid),
                        "metadata": message.metadata,
                    },
                },
                status=status.HTTP_200_OK,
            )

        except EmailMessage.DoesNotExist:
            return Response(
                {"code": 404, "message": "Threadline not found", "data": None},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            logger.error(f"Error updating metadata for {uuid}: {str(e)}")
            return Response(
                {"code": 400, "message": str(e), "data": None},
                status=status.HTTP_400_BAD_REQUEST,
            )
