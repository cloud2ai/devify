import pytest

from billing.models import BillingAuditLog
from billing.tasks import record_billing_audit_event


@pytest.mark.django_db
def test_record_billing_audit_event_is_idempotent():
    payload = {
        'event_key': 'audit-test-key-1',
        'action_type': 'credits.grant',
        'source': 'admin_api',
        'actor_name': 'admin',
        'target_username': 'target',
        'resource_type': 'credits_transaction',
        'resource_id': '123',
        'ip_address': '203.0.113.10',
        'user_agent': 'pytest',
        'before_data': {'bonus_credits': 0},
        'after_data': {'bonus_credits': 10},
        'context': {'amount': 10},
    }

    first = record_billing_audit_event(payload)
    second = record_billing_audit_event(payload)

    assert first['created'] is True
    assert second['created'] is False
    assert BillingAuditLog.objects.count() == 1
    log = BillingAuditLog.objects.get(event_key='audit-test-key-1')
    assert log.action_type == 'credits.grant'
    assert log.source == 'admin_api'
    assert log.context['amount'] == 10
