"""Relay Celery tasks."""

from __future__ import annotations

import logging

from celery import shared_task
from django.conf import settings

from agentcore_task.adapters.django import prevent_duplicate_task
from relay.models import RelayDelivery, RelayEvent
from relay.services.dispatcher import RelayDispatcher
from threadline.utils.task_tracer import TaskTracer

logger = logging.getLogger(__name__)


@shared_task
@prevent_duplicate_task(
    "process_relay_event",
    lock_param="event_id",
    timeout=getattr(settings, "TASK_TIMEOUT_MINUTES", 60) * 60,
)
def process_relay_event(event_id: str) -> dict:
    event = RelayEvent.objects.select_related("user", "email_message").get(
        id=event_id
    )
    tracer = TaskTracer("RELAY_DELIVERY", module="relay")
    task_id = getattr(process_relay_event.request, "id", "") or ""
    tracer.set_task_id(task_id)
    tracer.create_task(
        {
            "event_id": str(event.id),
            "email_message_id": str(event.email_message_id),
            "user_id": str(event.user_id),
            "status": "starting",
        }
    )
    try:
        event.status = RelayEvent.Status.PROCESSING
        event.save(update_fields=["status"])
        result = RelayDispatcher.dispatch_event(event, task_id=task_id)
        deliveries = RelayDelivery.objects.filter(event=event)
        tracer.complete_task(
            {
                "event_id": str(event.id),
                "status": "completed",
                "deliveries": deliveries.count(),
                "deliveries_success": result.get("success", 0),
                "deliveries_failed": result.get("failed", 0),
                "deliveries_skipped": result.get("skipped", 0),
            }
        )
        return result
    except Exception as exc:
        logger.exception("Relay event %s failed", event_id)
        event.status = RelayEvent.Status.FAILED
        event.save(update_fields=["status"])
        tracer.fail_task(
            {
                "event_id": str(event.id),
                "status": "failed",
                "error": str(exc),
            },
            str(exc),
        )
        raise


@shared_task
@prevent_duplicate_task(
    "process_relay_delivery",
    lock_param="delivery_id",
    timeout=getattr(settings, "TASK_TIMEOUT_MINUTES", 60) * 60,
)
def process_relay_delivery(delivery_id: str) -> dict:
    delivery = RelayDelivery.objects.select_related(
        "event",
        "event__user",
        "event__email_message",
        "subscription",
    ).get(id=delivery_id)
    tracer = TaskTracer("RELAY_DELIVERY", module="relay")
    task_id = getattr(process_relay_delivery.request, "id", "") or ""
    tracer.set_task_id(task_id)
    tracer.create_task(
        {
            "delivery_id": str(delivery.id),
            "event_id": str(delivery.event_id),
            "subscription_id": str(delivery.subscription_id),
            "user_id": str(delivery.event.user_id),
            "status": "starting",
        }
    )
    try:
        result = RelayDispatcher.retry_delivery(delivery, task_id=task_id)
        tracer.complete_task(
            {
                "delivery_id": str(delivery.id),
                "event_id": str(delivery.event_id),
                "status": "completed",
                "deliveries_success": result.get("success", 0),
                "deliveries_failed": result.get("failed", 0),
                "deliveries_skipped": result.get("skipped", 0),
            }
        )
        return result
    except Exception as exc:
        logger.exception("Relay delivery %s failed", delivery_id)
        delivery.status = RelayDelivery.Status.FAILED
        delivery.error_message = str(exc)
        delivery.save(update_fields=["status", "error_message", "updated_at"])
        tracer.fail_task(
            {
                "delivery_id": str(delivery.id),
                "event_id": str(delivery.event_id),
                "status": "failed",
                "error": str(exc),
            },
            str(exc),
        )
        raise
