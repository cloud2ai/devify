from __future__ import annotations

from datetime import datetime, timedelta, timezone as dt_timezone
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from django.utils import timezone

from billing.models import Plan, PlanPrice, Subscription, UserCredits
from billing.services.stripe_compat import StripePlanMappingError


def test_stripe_check_outcome_as_dict_uses_canonical_keys_only():
    from billing.services.payment_check.stripe import StripeCheckOutcome

    outcome = StripeCheckOutcome(
        provider='stripe',
        scanned_count=2,
        repaired_count=1,
        failed_count=0,
        manual_count=1,
        would_fix_count=3,
        in_sync_count=4,
        differences=[{'decision': 'fixed'}],
    )

    payload = outcome.as_dict()

    assert payload == {
        'provider': 'stripe',
        'scanned_count': 2,
        'repaired_count': 1,
        'failed_count': 0,
        'manual_count': 1,
        'would_fix_count': 3,
        'in_sync_count': 4,
        'differences': [{'decision': 'fixed'}],
    }
    assert 'checked_count' not in payload
    assert 'checked' not in payload
    assert 'fixed' not in payload
    assert 'errors' not in payload
    assert 'manual' not in payload
    assert 'would_fix' not in payload
    assert 'in_sync' not in payload
    assert 'results' not in payload


@pytest.mark.django_db
def test_payment_check_service_skips_platform_provider_and_aggregates_results(
    mocker,
):
    from billing.services.payment_check.service import PaymentCheckService

    fake_provider = SimpleNamespace(
        name='stripe',
        is_configured=Mock(return_value=True),
        run=Mock(
            return_value={
                'provider': 'stripe',
                'scanned_count': 2,
                'repaired_count': 1,
                'failed_count': 0,
                'manual_count': 0,
                'would_fix_count': 1,
                'in_sync_count': 1,
                'differences': [],
            }
        ),
    )
    mocker.patch(
        'billing.services.payment_check.service.get_payment_check_provider',
        return_value=fake_provider,
    )
    mocker.patch(
        'billing.services.payment_check.service.get_billing_config',
        return_value=SimpleNamespace(payment_check_providers=[]),
    )

    summary = PaymentCheckService.run(
        providers=['stripe', 'platform'],
        mode='report_only',
    )

    assert summary['mode'] == 'report_only'
    assert summary['requested_providers'] == ['stripe', 'platform']
    assert summary['skipped_providers'] == ['platform']
    assert summary['totals']['scanned_count'] == 2
    assert summary['totals']['would_fix_count'] == 1
    assert summary['totals']['repaired_count'] == 1
    assert 'checked_count' not in summary['totals']
    assert summary['providers'][0]['provider'] == 'stripe'
    fake_provider.run.assert_called_once_with(
        mode='report_only',
        actor_context=None,
    )


@pytest.mark.django_db
def test_stripe_payment_check_report_only_marks_safe_missing_subscription(
    mocker,
    test_user,
    starter_plan,
    payment_provider,
):
    from billing.services.payment_check.stripe import (
        StripePaymentCheckProvider,
    )

    PlanPrice.objects.create(
        plan=starter_plan,
        provider=payment_provider,
        provider_product_id='prod_test',
        provider_price_id='price_test',
        currency='USD',
        interval='month',
        unit_amount_cents=starter_plan.monthly_price_cents,
        is_active=True,
    )

    customer = SimpleNamespace(id='cus_123', subscriber=test_user)
    remote_subscription = SimpleNamespace(
        id='sub_123',
        status='active',
        created=200,
    )
    remote_subscription.to_dict = lambda: {
        'id': 'sub_123',
        'status': 'active',
        'customer': 'cus_123',
        'created': 200,
        'cancel_at_period_end': False,
        'items': {
            'data': [
                {
                    'price': {
                        'id': 'price_test',
                        'metadata': {'devify_plan_slug': 'starter'},
                    },
                    'current_period_start': 1710000000,
                    'current_period_end': 1712592000,
                }
            ]
        },
    }

    checker = StripePaymentCheckProvider()
    mocker.patch.object(checker, 'iter_targets', return_value=[customer])
    mocker.patch(
        'billing.services.payment_check.stripe.get_stripe_secret_key',
        return_value='sk_test_123',
    )
    mocker.patch(
        'billing.services.payment_check.stripe.stripe.Subscription.list',
        return_value=SimpleNamespace(data=[remote_subscription]),
    )
    sync_from_stripe_subscription = mocker.patch(
        'billing.services.payment_check.stripe.SubscriptionService.sync_from_stripe_subscription',
    )

    result = checker.run(mode='report_only')

    assert result['provider'] == 'stripe'
    assert result['scanned_count'] == 1
    assert result['would_fix_count'] == 1
    assert result['repaired_count'] == 0
    assert result['manual_count'] == 0
    assert result['differences'][0]['decision'] == 'would_fix'
    assert result['differences'][0]['reason'] == 'missing_local_subscription'
    sync_from_stripe_subscription.assert_not_called()


@pytest.mark.django_db
def test_stripe_payment_check_auto_fix_safe_reuses_existing_sync(
    mocker,
    test_user,
    starter_plan,
    payment_provider,
):
    from billing.services.payment_check.stripe import (
        StripePaymentCheckProvider,
    )

    PlanPrice.objects.create(
        plan=starter_plan,
        provider=payment_provider,
        provider_product_id='prod_test',
        provider_price_id='price_test',
        currency='USD',
        interval='month',
        unit_amount_cents=starter_plan.monthly_price_cents,
        is_active=True,
    )

    local_subscription = Subscription.objects.create(
        user=test_user,
        plan=starter_plan,
        provider=payment_provider,
        status='active',
        auto_renew=True,
        current_period_start=timezone.now() - timedelta(days=31),
        current_period_end=timezone.now() - timedelta(days=1),
    )
    UserCredits.objects.create(
        user=test_user,
        subscription=local_subscription,
        base_credits=starter_plan.metadata['credits_per_period'],
        consumed_credits=0,
        period_start=local_subscription.current_period_start,
        period_end=local_subscription.current_period_end,
        is_active=True,
    )

    customer = SimpleNamespace(id='cus_123', subscriber=test_user)
    remote_subscription = SimpleNamespace(
        id='sub_123',
        status='active',
        created=200,
    )
    remote_subscription.to_dict = lambda: {
        'id': 'sub_123',
        'status': 'active',
        'customer': 'cus_123',
        'created': 200,
        'cancel_at_period_end': False,
        'items': {
            'data': [
                {
                    'price': {
                        'id': 'price_test',
                        'metadata': {'devify_plan_slug': 'starter'},
                    },
                    'current_period_start': 1710000000,
                    'current_period_end': 1712592000,
                }
            ]
        },
    }

    checker = StripePaymentCheckProvider()
    mocker.patch.object(checker, 'iter_targets', return_value=[customer])
    mocker.patch(
        'billing.services.payment_check.stripe.get_stripe_secret_key',
        return_value='sk_test_123',
    )
    mocker.patch(
        'billing.services.payment_check.stripe.stripe.Subscription.list',
        return_value=SimpleNamespace(data=[remote_subscription]),
    )
    sync_from_stripe_subscription = mocker.patch(
        'billing.services.payment_check.stripe.SubscriptionService.sync_from_stripe_subscription',
        return_value=local_subscription,
    )
    audit_event = mocker.patch(
        'billing.services.payment_check.stripe.queue_billing_audit_event',
        return_value='audit_event_123',
    )

    result = checker.run(mode='auto_fix_safe')

    assert result['provider'] == 'stripe'
    assert result['scanned_count'] == 1
    assert result['repaired_count'] == 1
    assert result['would_fix_count'] == 0
    assert result['manual_count'] == 0
    assert result['differences'][0]['decision'] == 'fixed'
    sync_from_stripe_subscription.assert_called_once_with(remote_subscription)
    audit_event.assert_called_once()


@pytest.mark.django_db
def test_stripe_payment_check_auto_fix_safe_marks_unresolved_mapping_manual(
    mocker,
    test_user,
):
    from billing.services.payment_check.stripe import (
        StripePaymentCheckProvider,
    )

    customer = SimpleNamespace(id='cus_123', subscriber=test_user)
    remote_subscription = SimpleNamespace(
        id='sub_123',
        status='active',
        created=200,
    )
    remote_subscription.to_dict = lambda: {
        'id': 'sub_123',
        'status': 'active',
        'customer': 'cus_123',
        'created': 200,
        'cancel_at_period_end': False,
        'items': {
            'data': [
                {
                    'price': {
                        'id': 'price_missing',
                        'metadata': {},
                    },
                    'current_period_start': 1710000000,
                    'current_period_end': 1712592000,
                }
            ]
        },
    }

    checker = StripePaymentCheckProvider()
    mocker.patch.object(checker, 'iter_targets', return_value=[customer])
    mocker.patch(
        'billing.services.payment_check.stripe.get_stripe_secret_key',
        return_value='sk_test_123',
    )
    mocker.patch(
        'billing.services.payment_check.stripe.stripe.Subscription.list',
        return_value=SimpleNamespace(data=[remote_subscription]),
    )
    sync_from_stripe_subscription = mocker.patch(
        'billing.services.payment_check.stripe.SubscriptionService.sync_from_stripe_subscription',
        side_effect=StripePlanMappingError(price_id='price_missing'),
    )
    audit_event = mocker.patch(
        'billing.services.payment_check.stripe.queue_billing_audit_event',
        return_value='audit_event_123',
    )

    result = checker.run(mode='auto_fix_safe')

    assert result['provider'] == 'stripe'
    assert result['scanned_count'] == 1
    assert result['manual_count'] == 1
    assert result['would_fix_count'] == 0
    assert result['repaired_count'] == 0
    assert result['differences'][0]['decision'] == 'manual'
    assert result['differences'][0]['reason'] == 'unresolved_remote_plan_mapping'
    assert result['differences'][0]['remote_price_id'] == 'price_missing'
    sync_from_stripe_subscription.assert_called_once_with(remote_subscription)
    audit_event.assert_not_called()


@pytest.mark.django_db
def test_stripe_payment_check_marks_matching_active_subscription_in_sync(
    mocker,
    test_user,
    starter_plan,
    payment_provider,
):
    from billing.services.payment_check.stripe import (
        StripePaymentCheckProvider,
    )

    PlanPrice.objects.create(
        plan=starter_plan,
        provider=payment_provider,
        provider_product_id='prod_starter',
        provider_price_id='price_starter',
        currency='USD',
        interval='month',
        unit_amount_cents=starter_plan.monthly_price_cents,
        is_active=True,
    )

    local_subscription = Subscription.objects.create(
        user=test_user,
        plan=starter_plan,
        provider=payment_provider,
        status='active',
        auto_renew=True,
        current_period_start=datetime.fromtimestamp(1710000000, tz=dt_timezone.utc),
        current_period_end=datetime.fromtimestamp(1712592000, tz=dt_timezone.utc),
    )

    customer = SimpleNamespace(id='cus_123', subscriber=test_user)
    remote_subscription = SimpleNamespace(
        id='sub_123',
        status='active',
        created=200,
    )
    remote_subscription.to_dict = lambda: {
        'id': 'sub_123',
        'status': 'active',
        'customer': 'cus_123',
        'created': 200,
        'cancel_at_period_end': False,
        'items': {
            'data': [
                {
                    'price': {
                        'id': 'price_starter',
                        'metadata': {'devify_plan_slug': 'starter'},
                    },
                    'current_period_start': 1710000000,
                    'current_period_end': 1712592000,
                }
            ]
        },
    }

    checker = StripePaymentCheckProvider()
    mocker.patch.object(checker, 'iter_targets', return_value=[customer])
    mocker.patch(
        'billing.services.payment_check.stripe.get_stripe_secret_key',
        return_value='sk_test_123',
    )
    mocker.patch(
        'billing.services.payment_check.stripe.stripe.Subscription.list',
        return_value=SimpleNamespace(data=[remote_subscription]),
    )
    sync_from_stripe_subscription = mocker.patch(
        'billing.services.payment_check.stripe.SubscriptionService.sync_from_stripe_subscription',
        return_value=local_subscription,
    )

    result = checker.run(mode='report_only')

    assert result['provider'] == 'stripe'
    assert result['scanned_count'] == 1
    assert result['in_sync_count'] == 1
    assert result['would_fix_count'] == 0
    assert result['manual_count'] == 0
    assert result['differences'][0]['decision'] == 'in_sync'
    assert result['differences'][0]['reason'] == 'already_in_sync'
    sync_from_stripe_subscription.assert_not_called()


@pytest.mark.django_db
def test_stripe_payment_check_marks_plan_mismatch_would_fix(
    mocker,
    test_user,
    starter_plan,
    payment_provider,
):
    from billing.services.payment_check.stripe import (
        StripePaymentCheckProvider,
    )

    other_plan = Plan.objects.create(
        name='Pro',
        slug='pro',
        description='Pro plan',
        monthly_price_cents=2999,
        metadata={'credits_per_period': 100, 'period_days': 30},
        status='active',
        is_internal=False,
        allow_self_purchase=True,
    )

    PlanPrice.objects.create(
        plan=starter_plan,
        provider=payment_provider,
        provider_product_id='prod_starter',
        provider_price_id='price_starter',
        currency='USD',
        interval='month',
        unit_amount_cents=starter_plan.monthly_price_cents,
        is_active=True,
    )
    PlanPrice.objects.create(
        plan=other_plan,
        provider=payment_provider,
        provider_product_id='prod_other',
        provider_price_id='price_other',
        currency='USD',
        interval='month',
        unit_amount_cents=other_plan.monthly_price_cents,
        is_active=True,
    )

    local_subscription = Subscription.objects.create(
        user=test_user,
        plan=starter_plan,
        provider=payment_provider,
        status='active',
        auto_renew=True,
        current_period_start=timezone.now() - timedelta(days=31),
        current_period_end=timezone.now() - timedelta(days=1),
    )

    customer = SimpleNamespace(id='cus_123', subscriber=test_user)
    remote_subscription = SimpleNamespace(
        id='sub_123',
        status='active',
        created=200,
    )
    remote_subscription.to_dict = lambda: {
        'id': 'sub_123',
        'status': 'active',
        'customer': 'cus_123',
        'created': 200,
        'cancel_at_period_end': False,
        'items': {
            'data': [
                {
                    'price': {
                        'id': 'price_other',
                        'metadata': {'devify_plan_slug': 'pro'},
                    },
                    'current_period_start': 1710000000,
                    'current_period_end': 1712592000,
                }
            ]
        },
    }

    checker = StripePaymentCheckProvider()
    mocker.patch.object(checker, 'iter_targets', return_value=[customer])
    mocker.patch(
        'billing.services.payment_check.stripe.get_stripe_secret_key',
        return_value='sk_test_123',
    )
    mocker.patch(
        'billing.services.payment_check.stripe.stripe.Subscription.list',
        return_value=SimpleNamespace(data=[remote_subscription]),
    )
    sync_from_stripe_subscription = mocker.patch(
        'billing.services.payment_check.stripe.SubscriptionService.sync_from_stripe_subscription',
        return_value=local_subscription,
    )
    mocker.patch(
        'billing.services.payment_check.stripe.CreditsService.reset_period_credits'
    )
    mocker.patch(
        'billing.services.payment_check.stripe.queue_billing_audit_event',
        return_value='audit_event_123',
    )

    result = checker.run(mode='auto_fix_safe')

    assert result['provider'] == 'stripe'
    assert result['would_fix_count'] == 0
    assert result['repaired_count'] == 1
    assert result['differences'][0]['decision'] == 'fixed'
    assert result['differences'][0]['reason'] == 'stale_local_subscription'
    sync_from_stripe_subscription.assert_called_once_with(remote_subscription)


@pytest.mark.django_db
def test_stripe_payment_check_repairs_platform_subscription_when_remote_active(
    mocker,
    test_user,
    starter_plan,
    payment_provider,
    platform_payment_provider,
):
    from billing.services.payment_check.stripe import (
        StripePaymentCheckProvider,
    )

    PlanPrice.objects.create(
        plan=starter_plan,
        provider=payment_provider,
        provider_product_id='prod_starter',
        provider_price_id='price_starter',
        currency='USD',
        interval='month',
        unit_amount_cents=starter_plan.monthly_price_cents,
        is_active=True,
    )

    local_subscription = Subscription.objects.create(
        user=test_user,
        plan=starter_plan,
        provider=platform_payment_provider,
        status='active',
        auto_renew=True,
        current_period_start=datetime.fromtimestamp(1710000000, tz=dt_timezone.utc),
        current_period_end=datetime.fromtimestamp(1712592000, tz=dt_timezone.utc),
    )
    UserCredits.objects.create(
        user=test_user,
        subscription=local_subscription,
        base_credits=starter_plan.metadata['credits_per_period'],
        consumed_credits=0,
        period_start=local_subscription.current_period_start,
        period_end=local_subscription.current_period_end,
        is_active=True,
    )

    customer = SimpleNamespace(id='cus_123', subscriber=test_user)
    remote_subscription = SimpleNamespace(
        id='sub_123',
        status='active',
        created=200,
    )
    remote_subscription.to_dict = lambda: {
        'id': 'sub_123',
        'status': 'active',
        'customer': 'cus_123',
        'created': 200,
        'cancel_at_period_end': False,
        'items': {
            'data': [
                {
                    'price': {
                        'id': 'price_starter',
                        'metadata': {'devify_plan_slug': 'starter'},
                    },
                    'current_period_start': 1710000000,
                    'current_period_end': 1712592000,
                }
            ]
        },
    }

    checker = StripePaymentCheckProvider()
    mocker.patch.object(checker, 'iter_targets', return_value=[customer])
    mocker.patch(
        'billing.services.payment_check.stripe.get_stripe_secret_key',
        return_value='sk_test_123',
    )
    mocker.patch(
        'billing.services.payment_check.stripe.stripe.Subscription.list',
        return_value=SimpleNamespace(data=[remote_subscription]),
    )
    sync_from_stripe_subscription = mocker.patch(
        'billing.services.payment_check.stripe.SubscriptionService.sync_from_stripe_subscription',
        return_value=local_subscription,
    )

    result = checker.run(mode='report_only')

    assert result['provider'] == 'stripe'
    assert result['would_fix_count'] == 1
    assert result['repaired_count'] == 0
    assert result['differences'][0]['decision'] == 'would_fix'
    assert 'provider_mismatch' in result['differences'][0]['differences']
    sync_from_stripe_subscription.assert_not_called()


@pytest.mark.django_db
def test_stripe_payment_check_repairs_canceled_remote_subscription(
    mocker,
    test_user,
    starter_plan,
    payment_provider,
    platform_payment_provider,
):
    from billing.services.payment_check.stripe import (
        StripePaymentCheckProvider,
    )

    PlanPrice.objects.create(
        plan=starter_plan,
        provider=payment_provider,
        provider_product_id='prod_starter',
        provider_price_id='price_starter',
        currency='USD',
        interval='month',
        unit_amount_cents=starter_plan.monthly_price_cents,
        is_active=True,
    )

    local_subscription = Subscription.objects.create(
        user=test_user,
        plan=starter_plan,
        provider=platform_payment_provider,
        status='active',
        auto_renew=True,
        current_period_start=datetime.fromtimestamp(1710000000, tz=dt_timezone.utc),
        current_period_end=datetime.fromtimestamp(1712592000, tz=dt_timezone.utc),
    )
    UserCredits.objects.create(
        user=test_user,
        subscription=local_subscription,
        base_credits=starter_plan.metadata['credits_per_period'],
        consumed_credits=0,
        period_start=local_subscription.current_period_start,
        period_end=local_subscription.current_period_end,
        is_active=True,
    )

    customer = SimpleNamespace(id='cus_123', subscriber=test_user)
    remote_subscription = SimpleNamespace(
        id='sub_123',
        status='canceled',
        created=200,
    )
    remote_subscription.to_dict = lambda: {
        'id': 'sub_123',
        'status': 'canceled',
        'customer': 'cus_123',
        'created': 200,
        'cancel_at_period_end': False,
        'items': {
            'data': [
                {
                    'price': {
                        'id': 'price_starter',
                        'metadata': {'devify_plan_slug': 'starter'},
                    },
                    'current_period_start': 1710000000,
                    'current_period_end': 1712592000,
                }
            ]
        },
    }
    synced_subscription = Subscription.objects.create(
        user=test_user,
        plan=starter_plan,
        provider=payment_provider,
        status='canceled',
        auto_renew=False,
        current_period_start=datetime.fromtimestamp(1710000000, tz=dt_timezone.utc),
        current_period_end=datetime.fromtimestamp(1712592000, tz=dt_timezone.utc),
    )

    checker = StripePaymentCheckProvider()
    mocker.patch.object(checker, 'iter_targets', return_value=[customer])
    mocker.patch(
        'billing.services.payment_check.stripe.get_stripe_secret_key',
        return_value='sk_test_123',
    )
    mocker.patch(
        'billing.services.payment_check.stripe.stripe.Subscription.list',
        return_value=SimpleNamespace(data=[remote_subscription]),
    )
    sync_from_stripe_subscription = mocker.patch(
        'billing.services.payment_check.stripe.SubscriptionService.sync_from_stripe_subscription',
        return_value=synced_subscription,
    )

    result = checker.run(mode='auto_fix_safe')

    assert result['provider'] == 'stripe'
    assert result['scanned_count'] == 1
    assert result['repaired_count'] == 1
    assert result['would_fix_count'] == 0
    assert result['manual_count'] == 0
    assert result['differences'][0]['decision'] == 'fixed'
    assert result['differences'][0]['reason'] == 'remote_subscription_canceled'
    assert Subscription.objects.filter(user=test_user, status='active').count() == 0
    sync_from_stripe_subscription.assert_called_once_with(remote_subscription)
