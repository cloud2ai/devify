from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from django.conf import settings
from django.core.management import call_command

from billing.models import PaymentProvider, Plan
from billing.constants import get_payment_provider_display_name
from billing.services.config_service import get_billing_config


def load_plans_config(config_path: str | None = None) -> dict[str, Any]:
    if config_path:
        config_file = Path(config_path)
    else:
        base_path = Path(settings.BASE_DIR).parent
        config_file = base_path / 'conf' / 'billing' / 'plans.yaml'

    if not config_file.exists():
        raise FileNotFoundError(f'Plans config not found: {config_file}')

    with open(config_file, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f) or {}


def ensure_payment_provider(
    name: str,
    display_name: str,
    is_active: bool = True,
) -> PaymentProvider:
    provider, _ = PaymentProvider.objects.get_or_create(
        name=name,
        defaults={
            'display_name': display_name,
            'is_active': is_active,
        },
    )
    updated_fields: list[str] = []
    if provider.display_name != display_name:
        provider.display_name = display_name
        updated_fields.append('display_name')
    if provider.is_active != is_active:
        provider.is_active = is_active
        updated_fields.append('is_active')
    if updated_fields:
        provider.save(update_fields=updated_fields)
    return provider


def upsert_plans_from_config(plans_config: dict[str, Any]) -> list[Plan]:
    plans = plans_config.get('plans', [])
    upserted: list[Plan] = []

    for plan_data in plans:
        plan_data_copy = plan_data.copy()
        metadata = plan_data_copy.pop('metadata', {})
        status = plan_data_copy.pop('status', '')
        is_internal = plan_data_copy.pop('is_internal', False)
        allow_self_purchase = plan_data_copy.pop(
            'allow_self_purchase',
            False,
        )

        plan, created = Plan.objects.get_or_create(
            slug=plan_data_copy['slug'],
            defaults={
                **plan_data_copy,
                'metadata': metadata,
                'status': status,
                'is_internal': is_internal,
                'allow_self_purchase': allow_self_purchase,
            },
        )

        if not created:
            updated_fields: list[str] = []
            for field_name, field_value in plan_data_copy.items():
                if hasattr(plan, field_name):
                    current_value = getattr(plan, field_name)
                    if current_value != field_value:
                        setattr(plan, field_name, field_value)
                        updated_fields.append(field_name)

            if plan.metadata != metadata:
                plan.metadata = metadata
                updated_fields.append('metadata')

            if status and plan.status != status:
                plan.status = status
                updated_fields.append('status')

            if plan.is_internal != is_internal:
                plan.is_internal = is_internal
                updated_fields.append('is_internal')

            if plan.allow_self_purchase != allow_self_purchase:
                plan.allow_self_purchase = allow_self_purchase
                updated_fields.append('allow_self_purchase')

            if updated_fields:
                plan.save()

        upserted.append(plan)

    return upserted


def bootstrap_local_billing(
    *,
    config_path: str | None = None,
    initialize_credits: bool = True,
) -> dict[str, Any]:
    """
    Bootstrap local billing baseline data without touching Stripe products.
    """
    get_billing_config()
    ensure_payment_provider(
        'platform',
        get_payment_provider_display_name('platform'),
    )
    ensure_payment_provider(
        'stripe',
        get_payment_provider_display_name('stripe'),
    )
    plans_config = load_plans_config(config_path)
    plans = upsert_plans_from_config(plans_config)

    if initialize_credits:
        call_command('init_user_credits')

    return {
        'plans_count': len(plans),
        'credits_initialized': initialize_credits,
    }
