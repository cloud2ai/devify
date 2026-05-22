from __future__ import annotations

import logging
from datetime import date, datetime, time
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from django.conf import settings
from django.db import transaction

logger = logging.getLogger(__name__)

AUDIT_TASK_NAME = 'billing.tasks.record_billing_audit_event'


def _make_json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _make_json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_make_json_safe(item) for item in value]
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, UUID):
        return str(value)
    return value


def get_request_ip(request) -> str | None:
    """
    Resolve the client IP from a Django request.

    Prefer the first forwarded IP when available, then fall back to the
    direct remote address.
    """
    if request is None:
        return None

    forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if forwarded_for:
        first_ip = forwarded_for.split(',')[0].strip()
        if first_ip:
            return first_ip

    remote_addr = request.META.get('REMOTE_ADDR', '').strip()
    return remote_addr or None


def get_request_user_agent(request) -> str:
    if request is None:
        return ''
    return request.META.get('HTTP_USER_AGENT', '') or ''


def queue_billing_audit_event(
    *,
    action_type: str,
    source: str = 'system',
    actor_id: int | None = None,
    actor_name: str = '',
    target_user_id: int | None = None,
    target_username: str = '',
    resource_type: str = '',
    resource_id: str | int | None = '',
    ip_address: str | None = None,
    user_agent: str = '',
    before_data: dict[str, Any] | None = None,
    after_data: dict[str, Any] | None = None,
    context: dict[str, Any] | None = None,
    event_key: str | None = None,
) -> str:
    """
    Enqueue a billing audit event after the current transaction commits.

    The event is written by a Celery task so audit logging does not block the
    primary billing operation.
    """
    payload = {
        'event_key': event_key or str(uuid4()),
        'action_type': action_type,
        'source': source,
        'actor_id': actor_id,
        'actor_name': actor_name or '',
        'target_user_id': target_user_id,
        'target_username': target_username or '',
        'resource_type': resource_type or '',
        'resource_id': '' if resource_id is None else str(resource_id),
        'ip_address': ip_address,
        'user_agent': user_agent or '',
        'before_data': before_data or {},
        'after_data': after_data or {},
        'context': context or {},
    }
    payload = _make_json_safe(payload)

    def _enqueue():
        from billing.tasks import record_billing_audit_event

        if getattr(settings, 'CELERY_TASK_ALWAYS_EAGER', False):
            record_billing_audit_event.run(payload)
        else:
            record_billing_audit_event.delay(payload)

    if getattr(settings, 'CELERY_TASK_ALWAYS_EAGER', False):
        _enqueue()
        return payload['event_key']

    transaction.on_commit(_enqueue)
    logger.debug(
        'Queued billing audit event action_type=%s source=%s event_key=%s',
        action_type,
        source,
        payload['event_key'],
    )
    return payload['event_key']
