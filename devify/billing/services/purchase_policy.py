from __future__ import annotations

from billing.models import Plan, PlanPrice
from billing.services.config_service import get_public_billing_status


def can_user_purchase(
    plan: Plan,
    provider_name: str = 'stripe',
    billing_status: dict | None = None,
) -> bool:
    status = billing_status or get_public_billing_status()
    enabled_providers = status.get('enabled_providers') or []
    if not plan:
        return False

    return (
        plan.status == Plan.STATUS_ACTIVE
        and plan.allow_self_purchase
        and not plan.is_internal
        and bool(status.get('self_purchase_enabled'))
        and provider_name in enabled_providers
        and PlanPrice.objects.filter(
            plan=plan,
            provider__name=provider_name,
            is_active=True,
        ).exists()
    )
