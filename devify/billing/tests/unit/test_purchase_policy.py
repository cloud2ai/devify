import pytest

from billing.models import PaymentProvider, Plan, PlanPrice
from billing.services.purchase_policy import can_user_purchase


@pytest.mark.django_db
def test_can_user_purchase_requires_active_self_purchasable_plan():
    plan = Plan.objects.create(
        name='Pro',
        slug='pro',
        description='Pro plan',
        monthly_price_cents=2999,
        metadata={'credits_per_period': 100, 'period_days': 30},
        status='active',
        is_internal=False,
        allow_self_purchase=True,
    )
    provider, _ = PaymentProvider.objects.get_or_create(
        name='stripe',
        defaults={
            'display_name': 'Stripe',
            'is_active': True,
        },
    )
    PlanPrice.objects.create(
        plan=plan,
        provider=provider,
        provider_product_id='prod_test',
        provider_price_id='price_test',
        currency='USD',
        interval='month',
        unit_amount_cents=2999,
        is_active=True,
    )

    assert can_user_purchase(
        plan,
        'stripe',
        {
            'self_purchase_enabled': True,
            'enabled_providers': ['stripe'],
        },
    )


@pytest.mark.django_db
def test_can_user_purchase_rejects_admin_only_plan():
    plan = Plan.objects.create(
        name='Public Locked',
        slug='public-locked',
        description='Public but admin assigned only',
        monthly_price_cents=1999,
        metadata={'credits_per_period': 50, 'period_days': 30},
        status='active',
        is_internal=False,
        allow_self_purchase=False,
    )
    provider, _ = PaymentProvider.objects.get_or_create(
        name='stripe',
        defaults={
            'display_name': 'Stripe',
            'is_active': True,
        },
    )
    PlanPrice.objects.create(
        plan=plan,
        provider=provider,
        provider_product_id='prod_test',
        provider_price_id='price_test',
        currency='USD',
        interval='month',
        unit_amount_cents=1999,
        is_active=True,
    )

    assert not can_user_purchase(
        plan,
        'stripe',
        {
            'self_purchase_enabled': True,
            'enabled_providers': ['stripe'],
        },
    )


@pytest.mark.django_db
def test_can_user_purchase_rejects_disabled_provider():
    plan = Plan.objects.create(
        name='Pro',
        slug='pro',
        description='Pro plan',
        monthly_price_cents=2999,
        metadata={'credits_per_period': 100, 'period_days': 30},
        status='active',
        is_internal=False,
        allow_self_purchase=True,
    )
    provider, _ = PaymentProvider.objects.get_or_create(
        name='stripe',
        defaults={
            'display_name': 'Stripe',
            'is_active': True,
        },
    )
    PlanPrice.objects.create(
        plan=plan,
        provider=provider,
        provider_product_id='prod_test',
        provider_price_id='price_test',
        currency='USD',
        interval='month',
        unit_amount_cents=2999,
        is_active=True,
    )

    assert not can_user_purchase(
        plan,
        'stripe',
        {
            'self_purchase_enabled': True,
            'enabled_providers': [],
        },
    )
