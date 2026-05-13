"""Relay API views."""

from __future__ import annotations

import logging
import os
from types import SimpleNamespace

from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from agentcore_task.adapters.django.models import TaskExecution
from agentcore_metering.adapters.django.models import LLMConfig
from relay.models import RelayAppConfig, RelayDelivery, RelayEvent, RelaySubscription
from relay.serializers import (
    RelayAppConfigSerializer,
    RelayDeliverySerializer,
    RelayEventListSerializer,
    RelaySubscriptionSerializer,
)
from relay.services.adapters import RelayAdapterRegistry
from relay.services.test_attachments import (
    BUILTIN_TEST_ATTACHMENT,
    build_test_attachments,
)
from relay.tasks import process_relay_delivery
from relay.tasks import process_relay_event


logger = logging.getLogger(__name__)


def _response(data, message="ok", code=200, status_code=status.HTTP_200_OK):
    return Response({"code": code, "message": message, "data": data}, status=status_code)


def _build_test_email_message(snapshot: dict) -> SimpleNamespace:
    subject = (
        snapshot.get("summary_title")
        or snapshot.get("summary_content")
        or "Relay test"
    )
    return SimpleNamespace(
        id=0,
        subject=subject,
        summary_title=snapshot.get("summary_title") or subject,
        merged_into_id=None,
        merged_into=None,
    )


def _build_test_event(snapshot: dict) -> SimpleNamespace:
    return SimpleNamespace(
        email_message_id=0,
        artifact_snapshot=snapshot,
        email_message=_build_test_email_message(snapshot),
    )


def _build_test_delivery() -> SimpleNamespace:
    return SimpleNamespace(external_id=None, metadata={})


class AppsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        apps = [
            {
                "key": "relay",
                "name": _("Relay"),
                "name_zh": _("智能投递"),
                "path": "/apps/relay",
                "description": _("Route workflow completions to external tools."),
            }
        ]
        return _response(apps)


class RelaySubscriptionListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = RelaySubscription.objects.filter(user=request.user).order_by(
            "-created_at"
        )
        return _response(RelaySubscriptionSerializer(qs, many=True).data)

    def post(self, request):
        payload = dict(request.data or {})
        if not request.user.is_superuser:
            payload.pop("user_id", None)
        if "user_id" not in payload:
            payload["user_id"] = request.user.id
        serializer = RelaySubscriptionSerializer(
            data=payload, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        obj = serializer.save()
        return _response(
            RelaySubscriptionSerializer(obj, context={"request": request}).data,
            message=_("created"),
            code=201,
            status_code=status.HTTP_201_CREATED,
        )


class RelaySubscriptionDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_object(self, request, pk):
        return get_object_or_404(RelaySubscription, pk=pk, user=request.user)

    def patch(self, request, pk):
        obj = self._get_object(request, pk)
        serializer = RelaySubscriptionSerializer(
            obj, data=request.data, partial=True, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        obj = serializer.save()
        return _response(RelaySubscriptionSerializer(obj).data)

    def delete(self, request, pk):
        obj = self._get_object(request, pk)
        obj.delete()
        return _response(None, message=_("deleted"))


class RelayTestAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        subscription_id = request.data.get("subscription_id")
        if not subscription_id:
            return Response(
                {"code": 400, "message": "subscription_id is required", "data": None},
                status=status.HTTP_400_BAD_REQUEST,
        )
        subscription = get_object_or_404(
            RelaySubscription, pk=subscription_id, user=request.user
        )
        adapter = RelayAdapterRegistry.get_adapter(subscription.target_type)
        raw_attachments = request.data.get("attachments")
        temp_paths: list[str] = []
        try:
            try:
                test_attachments, temp_paths = build_test_attachments(
                    raw_attachments
                )
            except ValueError as exc:
                logger.warning(
                    "Invalid relay test attachments received; falling back to builtin sample: %s",
                    exc,
                )
                test_attachments, temp_paths = [], []

            if not test_attachments:
                test_attachments, temp_paths = build_test_attachments(
                    [BUILTIN_TEST_ATTACHMENT]
                )

            artifact_snapshot = request.data.get("artifact_snapshot") or {}
            artifact_snapshot = {
                **artifact_snapshot,
                "attachments": test_attachments,
                "attachment_count": len(test_attachments),
            }
            test_event = _build_test_event(artifact_snapshot)
            test_delivery = _build_test_delivery()
            result = adapter.deliver(
                event=test_event,
                subscription=subscription,
                delivery=test_delivery,
            )
            return _response(
                {
                    "external_id": result.external_id,
                    "external_url": result.external_url,
                    "metadata": result.metadata or {},
                    "attachment_count": len(test_attachments),
                }
            )
        except Exception as exc:
            logger.exception("Failed to run relay test delivery")
            return Response(
                {"code": 400, "message": str(exc), "data": None},
                status=status.HTTP_400_BAD_REQUEST,
            )
        finally:
            for path in temp_paths:
                try:
                    if path and os.path.exists(path):
                        os.remove(path)
                except OSError:
                    logger.warning(
                        "Failed to remove temporary relay test attachment file: %s",
                        path,
                    )


class RelayDeliveryListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            page = max(1, int(request.query_params.get("page", 1)))
        except (TypeError, ValueError):
            page = 1
        try:
            page_size = min(
                100,
                max(1, int(request.query_params.get("page_size", 20))),
            )
        except (TypeError, ValueError):
            page_size = 20

        qs = RelayDelivery.objects.filter(event__user=request.user).select_related(
            "event",
            "subscription",
        )
        total = qs.count()
        start = (page - 1) * page_size
        end = start + page_size
        items = qs.order_by("-created_at")[start:end]
        total_pages = max(1, (total + page_size - 1) // page_size)
        return _response(
            {
                "items": RelayDeliverySerializer(items, many=True).data,
                "pagination": {
                    "page": page,
                    "pageSize": page_size,
                    "total": total,
                    "totalPages": total_pages,
                    "hasNext": page < total_pages,
                    "hasPrevious": page > 1,
                },
            }
        )


class RelayDeliveryDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        obj = get_object_or_404(
            RelayDelivery.objects.select_related(
                "event",
                "subscription",
                "event__email_message",
            ),
            pk=pk,
            event__user=request.user,
        )
        return _response(RelayDeliverySerializer(obj).data)


class RelayEventListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            page = max(1, int(request.query_params.get("page", 1)))
        except (TypeError, ValueError):
            page = 1
        try:
            page_size = min(
                100,
                max(1, int(request.query_params.get("page_size", 20))),
            )
        except (TypeError, ValueError):
            page_size = 20

        qs = (
            RelayEvent.objects.filter(user=request.user)
            .select_related("email_message", "email_message__merged_into")
            .prefetch_related("deliveries")
        )
        total = qs.count()
        start = (page - 1) * page_size
        end = start + page_size
        items = qs.order_by("-created_at")[start:end]
        total_pages = max(1, (total + page_size - 1) // page_size)
        return _response(
            {
                "items": RelayEventListSerializer(items, many=True).data,
                "pagination": {
                    "page": page,
                    "pageSize": page_size,
                    "total": total,
                    "totalPages": total_pages,
                    "hasNext": page < total_pages,
                    "hasPrevious": page > 1,
                },
            }
        )


class RelayEventDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        obj = get_object_or_404(
            RelayEvent.objects.select_related(
                "email_message",
                "email_message__merged_into",
            ).prefetch_related("deliveries", "deliveries__subscription"),
            pk=pk,
            user=request.user,
        )
        return _response(RelayEventListSerializer(obj).data)


class RelayDeliveryRetryAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_object(self, request, pk):
        return get_object_or_404(
            RelayDelivery,
            pk=pk,
            event__user=request.user,
        )

    @staticmethod
    def _task_rebuilt_needed(delivery: RelayDelivery) -> bool:
        task_id = delivery.agentcore_task_id
        if not task_id:
            return False
        return not TaskExecution.objects.filter(task_id=task_id).exists()

    def post(self, request, pk):
        delivery = self._get_object(request, pk)
        task_rebuilt = self._task_rebuilt_needed(delivery)
        delivery.status = RelayDelivery.Status.PROCESSING
        delivery.error_message = ""
        delivery.metadata = {
            **(delivery.metadata or {}),
            "relay_retry_requested": True,
        }
        delivery.save(
            update_fields=[
                "status",
                "error_message",
                "metadata",
                "updated_at",
            ]
        )
        if delivery.event.status != RelayEvent.Status.PROCESSING:
            delivery.event.status = RelayEvent.Status.PROCESSING
            delivery.event.save(update_fields=["status"])
        task = process_relay_delivery.delay(str(delivery.id))
        return _response(
            {
                "delivery_id": delivery.id,
                "task_id": task.id,
                "task_rebuilt": task_rebuilt,
            },
            message=_("queued"),
            code=202,
            status_code=status.HTTP_202_ACCEPTED,
        )


class RelayEventRetryAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_object(self, request, pk):
        return get_object_or_404(
            RelayEvent,
            pk=pk,
            user=request.user,
        )

    @staticmethod
    def _task_rebuilt_needed(event: RelayEvent) -> bool:
        task_ids = list(
            event.deliveries.exclude(agentcore_task_id__isnull=True).exclude(
                agentcore_task_id=""
            ).values_list("agentcore_task_id", flat=True)
        )
        if not task_ids:
            return False
        existing_task_ids = set(
            TaskExecution.objects.filter(task_id__in=task_ids).values_list(
                "task_id", flat=True
            )
        )
        return any(task_id not in existing_task_ids for task_id in task_ids)

    def post(self, request, pk):
        event = self._get_object(request, pk)
        task_rebuilt = self._task_rebuilt_needed(event)
        if event.status != RelayEvent.Status.PROCESSING:
            event.status = RelayEvent.Status.PROCESSING
            event.save(update_fields=["status"])
        task = process_relay_event.delay(str(event.id))
        return _response(
            {
                "event_id": event.id,
                "task_id": task.id,
                "task_rebuilt": task_rebuilt,
            },
            message=_("queued"),
            code=202,
            status_code=status.HTTP_202_ACCEPTED,
        )


class RelayAdminConfigAPIView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        obj, _ = RelayAppConfig.objects.get_or_create(workflow_key="relay")
        return _response(RelayAppConfigSerializer(obj).data)

    def put(self, request):
        obj, _ = RelayAppConfig.objects.get_or_create(workflow_key="relay")
        serializer = RelayAppConfigSerializer(
            obj, data=request.data, partial=False, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        obj = serializer.save()
        return _response(RelayAppConfigSerializer(obj).data)


class RelayAdminLlmChoicesAPIView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        qs = LLMConfig.objects.filter(model_type=LLMConfig.MODEL_TYPE_LLM)
        data = [
            {
                "uuid": str(item.uuid),
                "provider": item.provider,
                "config": item.config,
                "model_type": item.model_type,
            }
            for item in qs.order_by("-created_at")[:200]
        ]
        return _response(data)
