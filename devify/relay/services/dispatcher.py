"""Relay event dispatcher."""

from __future__ import annotations

import logging
from typing import Any, Dict
from django.utils import timezone

from relay.models import RelayDelivery, RelayEvent, RelaySubscription
from relay.services.adapters import RelayAdapterRegistry
from relay.services.delivery_strategy import resolve_delivery_plan

logger = logging.getLogger(__name__)


class RelayDispatcher:
    """Dispatch relay events to all enabled subscriptions."""

    @classmethod
    def _delivery_payload(cls, event: RelayEvent) -> Dict[str, Any]:
        return {
            "event_id": str(event.id),
            "email_id": str(event.email_message_id),
            "user_id": str(event.user_id),
            "artifact_snapshot": event.artifact_snapshot or {},
        }

    @classmethod
    def dispatch_event(
        cls,
        event: RelayEvent,
        *,
        task_id: str | None = None,
    ) -> Dict[str, Any]:
        subscriptions = (
            RelaySubscription.objects.filter(user=event.user, enabled=True)
            .order_by("created_at")
        )
        summary = {"created": 0, "success": 0, "failed": 0, "skipped": 0}
        has_subscriptions = False

        for subscription in subscriptions:
            has_subscriptions = True
            idempotency_key = f"{event.id}:{subscription.id}"
            delivery, created = RelayDelivery.objects.get_or_create(
                idempotency_key=idempotency_key,
                defaults={
                    "event": event,
                    "subscription": subscription,
                    "target_type": subscription.target_type,
                    "status": RelayDelivery.Status.PENDING,
                    "agentcore_task_id": task_id,
                },
            )

            if created:
                summary["created"] += 1
            elif delivery.status == RelayDelivery.Status.SUCCESS:
                summary["skipped"] += 1
                continue
            elif delivery.status in {
                RelayDelivery.Status.PROCESSING,
                RelayDelivery.Status.PENDING,
            }:
                summary["skipped"] += 1
                continue

            if not created:
                delivery.subscription = subscription
                delivery.target_type = subscription.target_type
                delivery.status = RelayDelivery.Status.PENDING
                delivery.error_message = ""
                if task_id and not delivery.agentcore_task_id:
                    delivery.agentcore_task_id = task_id
                delivery.save(
                    update_fields=[
                        "subscription",
                        "target_type",
                        "status",
                        "error_message",
                        "agentcore_task_id",
                        "updated_at",
                    ]
                )

            try:
                cls._dispatch_one(
                    event=event,
                    subscription=subscription,
                    delivery=delivery,
                    task_id=task_id,
                )
                summary["success"] += 1
            except Exception as exc:
                summary["failed"] += 1
                logger.exception(
                    "Relay delivery failed event=%s subscription=%s",
                    event.id,
                    subscription.id,
                )
                delivery.status = RelayDelivery.Status.FAILED
                delivery.error_message = str(exc)
                delivery.metadata = {
                    **(delivery.metadata or {}),
                    "error": str(exc),
                }
                delivery.save(
                    update_fields=[
                        "status",
                        "error_message",
                        "metadata",
                        "updated_at",
                    ]
                )

        if summary["failed"]:
            event.status = RelayEvent.Status.FAILED
        elif has_subscriptions and not summary["success"]:
            event.status = RelayEvent.Status.FAILED
        else:
            event.status = RelayEvent.Status.COMPLETED
        event.processed_at = timezone.now()
        event.save(update_fields=["status", "processed_at"])
        return summary

    @classmethod
    def retry_delivery(
        cls,
        delivery: RelayDelivery,
        *,
        task_id: str | None = None,
    ) -> Dict[str, Any]:
        delivery = (
            RelayDelivery.objects.select_related(
                "event",
                "event__user",
                "event__email_message",
                "subscription",
            )
            .get(id=delivery.id)
        )

        delivery.status = RelayDelivery.Status.PENDING
        delivery.error_message = ""
        delivery.metadata = {
            **(delivery.metadata or {}),
            "relay_retry_requested": True,
        }
        if task_id:
            delivery.agentcore_task_id = task_id
        delivery.save(
            update_fields=[
                "status",
                "error_message",
                "metadata",
                "agentcore_task_id",
                "updated_at",
            ]
        )

        _dispatch_failed = False
        try:
            cls._dispatch_one(
                event=delivery.event,
                subscription=delivery.subscription,
                delivery=delivery,
                task_id=task_id,
            )
        except Exception:
            _dispatch_failed = True
            raise
        finally:
            if _dispatch_failed:
                delivery.event.status = RelayEvent.Status.FAILED
            else:
                failed_count = RelayDelivery.objects.filter(
                    event=delivery.event,
                    status=RelayDelivery.Status.FAILED,
                ).count()
                delivery.event.status = (
                    RelayEvent.Status.FAILED if failed_count
                    else RelayEvent.Status.COMPLETED
                )
            delivery.event.processed_at = timezone.now()
            delivery.event.save(update_fields=["status", "processed_at"])
        return {"created": 0, "success": 1, "failed": 0, "skipped": 0}

    @classmethod
    def _dispatch_one(
        cls,
        *,
        event,
        subscription,
        delivery,
        task_id: str | None = None,
    ) -> None:
        adapter = RelayAdapterRegistry.get_adapter(subscription.target_type)
        plan = resolve_delivery_plan(subscription, event, delivery)
        delivery.metadata = {
            **(delivery.metadata or {}),
            "relay_delivery_plan": plan,
        }
        if (
            plan.get("action") == "update"
            and plan.get("reference_external_id")
            and not delivery.external_id
        ):
            delivery.external_id = plan["reference_external_id"]
        delivery.status = RelayDelivery.Status.PROCESSING
        if task_id and not delivery.agentcore_task_id:
            delivery.agentcore_task_id = task_id
        delivery.save(
            update_fields=[
                "status",
                "external_id",
                "metadata",
                "agentcore_task_id",
                "updated_at",
            ]
        )

        result = adapter.deliver(
            event=event,
            subscription=subscription,
            delivery=delivery,
        )
        delivery.status = RelayDelivery.Status.SUCCESS
        delivery.external_id = result.external_id
        delivery.external_url = result.external_url
        delivery.metadata = {
            **(delivery.metadata or {}),
            **(result.metadata or {}),
        }
        delivery.save(
            update_fields=[
                "status",
                "external_id",
                "external_url",
                "metadata",
                "agentcore_task_id",
                "updated_at",
            ]
        )
