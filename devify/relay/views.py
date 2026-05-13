"""Relay API views."""

from __future__ import annotations

import logging
import os
from copy import deepcopy
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


def _deep_merge_dicts(base, override):
    merged = dict(base or {})
    for key, value in (override or {}).items():
        existing = merged.get(key)
        if isinstance(existing, dict) and isinstance(value, dict):
            merged[key] = _deep_merge_dicts(existing, value)
        else:
            merged[key] = value
    return merged


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
        draft_subscription = request.data.get("subscription")
        subscription = None
        if subscription_id:
            subscription = get_object_or_404(
                RelaySubscription, pk=subscription_id, user=request.user
            )
        elif not isinstance(draft_subscription, dict):
            return Response(
                {
                    "code": 400,
                    "message": "subscription_id or subscription is required",
                    "data": None,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        draft_target_type = (
            draft_subscription or {}
        ).get("target_type")
        target_type = (
            draft_target_type
            or (subscription.target_type if subscription else None)
            or request.data.get("target_type")
            or RelaySubscription.TargetType.FEISHU_BITABLE
        )
        config_override = (
            request.data.get("config")
            if isinstance(request.data.get("config"), dict)
            else None
        )
        strategies_override = (
            request.data.get("strategies")
            if isinstance(request.data.get("strategies"), dict)
            else None
        )
        field_mappings_override = (
            request.data.get("field_mappings")
            if isinstance(request.data.get("field_mappings"), dict)
            else None
        )

        draft_config = (
            deepcopy((draft_subscription or {}).get("config") or {})
            if isinstance(draft_subscription, dict)
            else {}
        )
        draft_strategies = (
            deepcopy((draft_subscription or {}).get("strategies") or {})
            if isinstance(draft_subscription, dict)
            else {}
        )
        draft_field_mappings = (
            deepcopy((draft_subscription or {}).get("field_mappings") or {})
            if isinstance(draft_subscription, dict)
            else {}
        )

        if subscription:
            resolved_config = _deep_merge_dicts(
                subscription.config or {},
                config_override or {},
            )
            if draft_config:
                resolved_config = _deep_merge_dicts(
                    resolved_config,
                    draft_config,
                )
            resolved_strategies = _deep_merge_dicts(
                subscription.strategies or {},
                strategies_override or {},
            )
            if draft_strategies:
                resolved_strategies = _deep_merge_dicts(
                    resolved_strategies,
                    draft_strategies,
                )
            resolved_field_mappings = _deep_merge_dicts(
                subscription.field_mappings or {},
                field_mappings_override or {},
            )
            if draft_field_mappings:
                resolved_field_mappings = _deep_merge_dicts(
                    resolved_field_mappings,
                    draft_field_mappings,
                )
        else:
            resolved_config = draft_config
            if config_override:
                resolved_config = _deep_merge_dicts(
                    resolved_config,
                    config_override,
                )
            resolved_strategies = draft_strategies
            if strategies_override:
                resolved_strategies = _deep_merge_dicts(
                    resolved_strategies,
                    strategies_override,
                )
            resolved_field_mappings = draft_field_mappings
            if field_mappings_override:
                resolved_field_mappings = _deep_merge_dicts(
                    resolved_field_mappings,
                    field_mappings_override,
                )

        effective_subscription = SimpleNamespace(
            id=getattr(subscription, "id", None),
            user=request.user,
            target_type=target_type,
            config=resolved_config,
            strategies=resolved_strategies,
            field_mappings=resolved_field_mappings,
        )
        adapter = RelayAdapterRegistry.get_adapter(target_type)
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
            test_delivery.metadata["relay_delivery_plan"] = {
                "action": "new",
                "source": "test",
                "reference_external_id": "",
                "reference_delivery_id": None,
                "related_issue_keys": [],
                "linking_supported": False,
            }
            result = adapter.deliver(
                event=test_event,
                subscription=effective_subscription,
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
