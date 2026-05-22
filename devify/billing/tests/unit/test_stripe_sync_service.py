from types import SimpleNamespace

import pytest

from billing.models import Plan, PlanPrice, PaymentProvider
from billing.services.stripe_sync_service import StripePlanSyncService


@pytest.mark.django_db
def test_sync_plan_to_stripe_creates_plan_price(mocker):
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

    mocker.patch(
        'billing.services.stripe_sync_service.get_stripe_secret_key',
        return_value='sk_test_123',
    )
    mocker.patch(
        'billing.services.stripe_sync_service.stripe.Product.search',
        return_value=SimpleNamespace(data=[]),
    )
    mocker.patch(
        'billing.services.stripe_sync_service.stripe.Product.create',
        return_value=SimpleNamespace(id='prod_test'),
    )
    mocker.patch(
        'billing.services.stripe_sync_service.stripe.Price.list',
        return_value=SimpleNamespace(data=[]),
    )
    mocker.patch(
        'billing.services.stripe_sync_service.stripe.Price.create',
        return_value=SimpleNamespace(id='price_test'),
    )

    result = StripePlanSyncService.sync_plan(plan)

    assert result['provider_name'] == 'stripe'
    assert result['provider_product_id'] == 'prod_test'
    assert result['provider_price_id'] == 'price_test'
    assert result['created_new_price'] is True
    assert PaymentProvider.objects.filter(name='stripe').exists()
    plan_price = PlanPrice.objects.get(plan=plan, provider__name='stripe')
    assert plan_price.provider_price_id == 'price_test'
    assert plan_price.provider_product_id == 'prod_test'
    assert plan_price.unit_amount_cents == 2999


@pytest.mark.django_db
def test_sync_plan_to_stripe_reuses_matching_price_without_metadata_get(mocker):
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

    mocker.patch(
        'billing.services.stripe_sync_service.get_stripe_secret_key',
        return_value='sk_test_123',
    )
    mocker.patch(
        'billing.services.stripe_sync_service.stripe.Product.search',
        return_value=SimpleNamespace(data=[]),
    )
    mocker.patch(
        'billing.services.stripe_sync_service.stripe.Product.create',
        return_value=SimpleNamespace(id='prod_test'),
    )
    mocker.patch(
        'billing.services.stripe_sync_service.stripe.Price.list',
        return_value=SimpleNamespace(
            data=[
                SimpleNamespace(
                    id='price_existing',
                    unit_amount=2999,
                    metadata=SimpleNamespace(devify_plan_slug='pro'),
                )
            ]
        ),
    )
    price_create = mocker.patch(
        'billing.services.stripe_sync_service.stripe.Price.create',
    )

    result = StripePlanSyncService.sync_plan(plan)

    assert result['provider_price_id'] == 'price_existing'
    assert result['created_new_price'] is False
    price_create.assert_not_called()
