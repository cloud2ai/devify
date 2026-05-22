from datetime import timedelta
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

from billing.models import (
    BillingAuditLog,
    Plan,
    PaymentProvider,
    PlanPrice,
    Subscription,
    UserCredits,
)
from billing.services.subscription_service import SubscriptionService


User = get_user_model()


@pytest.mark.django_db
def test_admin_billing_config_requires_admin():
    admin_user = User.objects.create_superuser(
        username='billing-admin',
        email='billing-admin@example.com',
        password='secret12345',
    )
    normal_user = User.objects.create_user(
        username='billing-user',
        email='billing-user@example.com',
        password='secret12345',
    )

    admin_client = APIClient()
    admin_client.force_authenticate(user=admin_user)

    response = admin_client.get('/api/v1/admin/billing/config')

    assert response.status_code == 200
    payload = response.json()['data']
    assert 'stripe_configured' in payload
    assert 'recharge_enabled' in payload
    assert 'self_purchase_enabled' in payload
    assert 'enabled_providers' in payload
    assert 'payment_callback_url' in payload
    assert 'payment_check_enabled' in payload
    assert 'payment_check_providers' in payload
    assert 'payment_check_schedule' in payload
    assert 'payment_record_backfill_enabled' in payload
    assert 'payment_record_backfill_schedule' in payload
    assert 'payment_record_backfill_lookback_days' in payload

    user_client = APIClient()
    user_client.force_authenticate(user=normal_user)

    forbidden_response = user_client.get('/api/v1/admin/billing/config')

    assert forbidden_response.status_code == 403


@pytest.mark.django_db
def test_admin_can_update_billing_config_self_purchase_controls():
    admin_user = User.objects.create_superuser(
        username='billing-admin',
        email='billing-admin@example.com',
        password='secret12345',
    )
    admin_client = APIClient()
    admin_client.force_authenticate(user=admin_user)

    response = admin_client.put(
        '/api/v1/admin/billing/config',
        {
            'self_purchase_enabled': True,
            'enabled_providers': ['stripe'],
            'payment_callback_url': 'http://callback.example',
            'payment_check_enabled': True,
            'payment_check_providers': ['stripe', 'platform'],
            'payment_check_schedule': '0 */15 * * *',
            'payment_record_backfill_enabled': True,
            'payment_record_backfill_schedule': '0 */20 * * *',
            'payment_record_backfill_lookback_days': 14,
        },
        format='json',
    )

    assert response.status_code == 200
    payload = response.json()['data']
    assert payload['self_purchase_enabled'] is True
    assert payload['enabled_providers'] == ['stripe']
    assert payload['payment_callback_url'] == 'http://callback.example'
    assert payload['payment_check_enabled'] is True
    assert payload['payment_check_providers'] == ['stripe', 'platform']
    assert payload['payment_check_schedule'] == '0 */15 * * *'
    assert payload['payment_record_backfill_enabled'] is True
    assert payload['payment_record_backfill_schedule'] == '0 */20 * * *'
    assert payload['payment_record_backfill_lookback_days'] == 14
    assert payload['recharge_enabled'] in {True, False}


@pytest.mark.django_db
def test_public_billing_status_is_available_to_authenticated_users():
    user = User.objects.create_user(
        username='status-user',
        email='status-user@example.com',
        password='secret12345',
    )

    client = APIClient()
    client.force_authenticate(user=user)

    response = client.get('/api/billing/status')

    assert response.status_code == 200
    payload = response.json()['data']
    assert payload['billing_active'] is True
    assert payload['credits_enabled'] is True
    assert payload['admin_grant_enabled'] is True
    assert 'recharge_enabled' in payload
    assert 'self_purchase_enabled' in payload
    assert 'enabled_providers' in payload
    assert payload['provider'] == 'stripe'


@pytest.mark.django_db
def test_admin_billing_plans_list_includes_stripe_mapping():
    admin_user = User.objects.create_superuser(
        username='billing-admin',
        email='billing-admin@example.com',
        password='secret12345',
    )
    admin_client = APIClient()
    admin_client.force_authenticate(user=admin_user)

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
    provider = PaymentProvider.objects.create(
        name='stripe',
        display_name='Stripe',
        is_active=True,
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

    response = admin_client.get('/api/v1/admin/billing/plans')

    assert response.status_code == 200
    payload = response.json()['data']
    assert len(payload) == 1
    assert payload[0]['slug'] == 'pro'
    assert payload[0]['status'] == 'active'
    assert payload[0]['allow_self_purchase'] is True
    assert payload[0]['stripe_price_id'] == 'price_test'
    assert payload[0]['stripe_product_id'] == 'prod_test'


@pytest.mark.django_db
def test_plan_with_stripe_data_uses_prefetched_prices_without_query(mocker):
    from billing.admin_views import _plan_with_stripe_data

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
    plan.stripe_plan_prices = [
        PlanPrice(
            provider_price_id='price_test',
            provider_product_id='prod_test',
        )
    ]
    mocker.patch(
        'billing.admin_views.PlanPrice.objects.filter',
        side_effect=AssertionError('Unexpected PlanPrice query'),
    )

    plan_data = _plan_with_stripe_data(plan)

    assert plan_data['stripe_price_id'] == 'price_test'
    assert plan_data['stripe_product_id'] == 'prod_test'


@pytest.mark.django_db
def test_admin_billing_users_list_includes_users_without_credits():
    admin_user = User.objects.create_superuser(
        username='billing-admin',
        email='billing-admin@example.com',
        password='secret12345',
    )
    User.objects.create_user(
        username='billing-no-credits',
        email='billing-no-credits@example.com',
        password='secret12345',
    )

    admin_client = APIClient()
    admin_client.force_authenticate(user=admin_user)

    response = admin_client.get('/api/v1/admin/billing/users')

    assert response.status_code == 200
    payload = response.json()['data']
    assert payload['count'] == 2
    row = next(
        item
        for item in payload['results']
        if item['username'] == 'billing-no-credits'
    )
    assert row['available_credits'] == 0
    assert row['plan_slug'] is None
    assert row['plan_name'] is None


@pytest.mark.django_db
def test_admin_billing_users_list_does_not_embed_identity_conflicts(mocker):
    admin_user = User.objects.create_superuser(
        username='billing-admin',
        email='billing-admin@example.com',
        password='secret12345',
    )
    User.objects.create_user(
        username='billing-normal',
        email='billing-normal@example.com',
        password='secret12345',
    )

    admin_client = APIClient()
    admin_client.force_authenticate(user=admin_user)

    response = admin_client.get('/api/v1/admin/billing/users')

    assert response.status_code == 200
    payload = response.json()['data']
    row = next(
        item
        for item in payload['results']
        if item['username'] == 'billing-normal'
    )
    assert 'identity_conflict' not in row
    assert 'identity_conflict_count' not in row
    assert 'identity_conflict_customers' not in row


@pytest.mark.django_db
def test_admin_billing_identity_conflicts_endpoint_returns_conflicts(mocker):
    admin_user = User.objects.create_superuser(
        username='billing-admin',
        email='billing-admin@example.com',
        password='secret12345',
    )
    conflicted_user = User.objects.create_user(
        username='billing-conflict',
        email='billing-conflict@example.com',
        password='secret12345',
    )
    User.objects.create_user(
        username='billing-normal',
        email='billing-normal@example.com',
        password='secret12345',
    )

    mocker.patch(
        'billing.admin_views.summarize_customer_identity_for_user',
        side_effect=lambda user: {
            'has_conflict': user.id == conflicted_user.id,
            'match_count': 2 if user.id == conflicted_user.id else 1,
            'customers': (
                [
                    {
                        'id': 'cus_a',
                        'subscriber_id': conflicted_user.id,
                        'subscriber_username': 'billing-conflict',
                        'match_sources': ['subscriber'],
                        'email': 'a@example.com',
                    },
                    {
                        'id': 'cus_b',
                        'subscriber_id': conflicted_user.id,
                        'subscriber_username': 'billing-conflict',
                        'match_sources': ['subscriber'],
                        'email': 'b@example.com',
                    },
                ]
                if user.id == conflicted_user.id
                else []
            ),
        },
    )

    admin_client = APIClient()
    admin_client.force_authenticate(user=admin_user)

    response = admin_client.get('/api/v1/admin/billing/identity-conflicts')

    assert response.status_code == 200
    payload = response.json()['data']
    assert payload['count'] == 1
    conflicted_row = payload['results'][0]
    assert conflicted_row['username'] == 'billing-conflict'
    assert conflicted_row['match_count'] == 2
    assert len(conflicted_row['customers']) == 2


@pytest.mark.django_db
def test_admin_can_update_billing_plan():
    admin_user = User.objects.create_superuser(
        username='billing-admin',
        email='billing-admin@example.com',
        password='secret12345',
    )
    admin_client = APIClient()
    admin_client.force_authenticate(user=admin_user)

    plan = Plan.objects.create(
        name='Starter',
        slug='starter',
        description='Starter plan',
        monthly_price_cents=999,
        metadata={'credits_per_period': 10, 'period_days': 30},
        status='active',
        is_internal=False,
        allow_self_purchase=True,
    )

    response = admin_client.put(
        f'/api/v1/admin/billing/plans/{plan.id}',
        {
            'name': 'Starter Plus',
            'slug': 'starter-plus',
            'description': 'Updated plan',
            'monthly_price_cents': 1999,
            'metadata': {'credits_per_period': 20, 'period_days': 45},
            'status': 'draft',
            'is_internal': True,
            'allow_self_purchase': False,
        },
        format='json',
    )

    assert response.status_code == 200
    payload = response.json()['data']
    assert payload['name'] == 'Starter Plus'
    assert payload['slug'] == 'starter-plus'
    assert payload['monthly_price_cents'] == 1999
    assert payload['metadata']['credits_per_period'] == 20
    assert payload['status'] == 'draft'
    assert payload['is_active'] is False
    assert payload['is_internal'] is True
    assert payload['allow_self_purchase'] is False


@pytest.mark.django_db
def test_admin_plan_status_only_update_keeps_is_active_in_sync():
    admin_user = User.objects.create_superuser(
        username='billing-admin',
        email='billing-admin@example.com',
        password='secret12345',
    )
    admin_client = APIClient()
    admin_client.force_authenticate(user=admin_user)

    plan = Plan.objects.create(
        name='Starter',
        slug='starter',
        description='Starter plan',
        monthly_price_cents=999,
        metadata={'credits_per_period': 10, 'period_days': 30},
        status='active',
        is_internal=False,
        allow_self_purchase=True,
    )

    response = admin_client.put(
        f'/api/v1/admin/billing/plans/{plan.id}',
        {
            'status': 'draft',
        },
        format='json',
    )

    assert response.status_code == 200
    payload = response.json()['data']
    assert payload['status'] == 'draft'
    assert payload['is_active'] is False


@pytest.mark.django_db
def test_admin_can_sync_plan_to_stripe():
    admin_user = User.objects.create_superuser(
        username='billing-admin',
        email='billing-admin@example.com',
        password='secret12345',
    )
    admin_client = APIClient()
    admin_client.force_authenticate(user=admin_user)

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

    def fake_sync(target_plan):
        provider, _ = PaymentProvider.objects.get_or_create(
            name='stripe',
            defaults={'display_name': 'Stripe', 'is_active': True},
        )
        plan_price, _ = PlanPrice.objects.update_or_create(
            plan=target_plan,
            provider=provider,
            interval='month',
            defaults={
                'provider_product_id': 'prod_test',
                'provider_price_id': 'price_test',
                'currency': 'USD',
                'unit_amount_cents': target_plan.monthly_price_cents,
                'is_active': True,
            },
        )
        return {
            'provider_name': 'stripe',
            'plan_price_id': plan_price.id,
            'provider_product_id': 'prod_test',
            'provider_price_id': 'price_test',
            'created_new_price': True,
            'deactivated_price_id': None,
        }

    with patch(
        'billing.admin_views.StripePlanSyncService.sync_plan',
        side_effect=fake_sync,
    ):
        response = admin_client.post(
            f'/api/v1/admin/billing/plans/{plan.id}/sync-stripe',
            format='json',
        )

    assert response.status_code == 200
    payload = response.json()['data']
    assert payload['plan']['stripe_price_id'] == 'price_test'
    assert payload['plan']['stripe_product_id'] == 'prod_test'
    assert payload['sync_result']['provider_price_id'] == 'price_test'

    assert BillingAuditLog.objects.filter(
        action_type='plan.sync_stripe',
        resource_type='plan',
        resource_id=str(plan.id),
    ).exists()


@pytest.mark.django_db
def test_admin_can_assign_free_subscription_to_user_without_one(
    free_plan,
):
    admin_user = User.objects.create_superuser(
        username='billing-admin',
        email='billing-admin@example.com',
        password='secret12345',
    )
    user = User.objects.create_user(
        username='billing-free-user',
        email='billing-free-user@example.com',
        password='secret12345',
    )
    UserCredits.objects.create(
        user=user,
        base_credits=0,
        bonus_credits=0,
        consumed_credits=0,
        period_start=timezone.now(),
        period_end=timezone.now(),
        is_active=True,
    )

    admin_client = APIClient()
    admin_client.force_authenticate(user=admin_user)

    response = admin_client.post(
        f'/api/v1/admin/billing/users/{user.id}/assign-plan',
        {'plan_slug': 'free'},
        format='json',
    )

    assert response.status_code == 201
    payload = response.json()['data']
    assert payload['created'] is True
    assert payload['subscription']['plan_slug'] == 'free'
    assert payload['subscription']['status'] == 'active'
    assert payload['credits']['base_credits'] == free_plan.metadata[
        'credits_per_period'
    ]

    credits = UserCredits.objects.get(user=user, is_active=True)
    assert credits.subscription is not None
    assert credits.subscription.plan.slug == 'free'


@pytest.mark.django_db
def test_admin_can_sync_user_subscription_from_stripe():
    admin_user = User.objects.create_superuser(
        username='billing-admin',
        email='billing-admin@example.com',
        password='secret12345',
    )
    user = User.objects.create_user(
        username='billing-stripe-recovery',
        email='billing-stripe-recovery@example.com',
        password='secret12345',
    )
    starter_plan = Plan.objects.create(
        name='Starter',
        slug='starter',
        description='Starter plan',
        monthly_price_cents=999,
        metadata={'credits_per_period': 100, 'period_days': 30},
        status='active',
        is_internal=False,
        allow_self_purchase=True,
    )
    payment_provider = PaymentProvider.objects.create(
        name='stripe',
        display_name='Stripe',
        is_active=True,
    )
    subscription = Subscription.objects.create(
        user=user,
        plan=starter_plan,
        provider=payment_provider,
        status='active',
        auto_renew=True,
        current_period_start=timezone.now(),
        current_period_end=timezone.now() + timedelta(days=30),
    )
    UserCredits.objects.create(
        user=user,
        subscription=subscription,
        base_credits=starter_plan.metadata['credits_per_period'],
        bonus_credits=0,
        consumed_credits=0,
        period_start=timezone.now(),
        period_end=timezone.now() + timedelta(days=30),
        is_active=True,
    )

    admin_client = APIClient()
    admin_client.force_authenticate(user=admin_user)

    with patch(
        'billing.admin_views.SubscriptionService.sync_user_subscription_from_stripe',
        return_value=subscription,
    ) as mock_sync:
        response = admin_client.post(
            f'/api/v1/admin/billing/users/{user.id}/sync-stripe',
            format='json',
            HTTP_X_FORWARDED_FOR='203.0.113.42',
        )

    assert response.status_code == 200
    payload = response.json()['data']
    assert payload['subscription']['plan_slug'] == 'starter'
    assert payload['subscription']['provider_name'] == 'Stripe'
    mock_sync.assert_called_once_with(user)
    assert BillingAuditLog.objects.filter(
        action_type='subscription.sync_stripe',
        resource_type='subscription',
        resource_id=str(subscription.id),
    ).exists()


@pytest.mark.django_db
def test_admin_sync_user_subscription_surfaces_real_error_message():
    admin_user = User.objects.create_superuser(
        username='billing-admin-error',
        email='billing-admin-error@example.com',
        password='secret12345',
    )
    user = User.objects.create_user(
        username='billing-stripe-error',
        email='billing-stripe-error@example.com',
        password='secret12345',
    )

    admin_client = APIClient()
    admin_client.force_authenticate(user=admin_user)

    with patch(
        'billing.admin_views.SubscriptionService.sync_user_subscription_from_stripe',
        side_effect=AttributeError('get'),
    ):
        response = admin_client.post(
            f'/api/v1/admin/billing/users/{user.id}/sync-stripe',
            format='json',
            HTTP_X_FORWARDED_FOR='203.0.113.42',
        )

    assert response.status_code == 400
    payload = response.json()['data']
    assert payload['user_id'] == 'AttributeError: get'


@pytest.mark.django_db
def test_admin_sync_user_subscription_surfaces_real_error_message():
    admin_user = User.objects.create_superuser(
        username='billing-admin-error',
        email='billing-admin-error@example.com',
        password='secret12345',
    )
    user = User.objects.create_user(
        username='billing-stripe-error',
        email='billing-stripe-error@example.com',
        password='secret12345',
    )

    admin_client = APIClient()
    admin_client.force_authenticate(user=admin_user)

    with patch(
        'billing.admin_views.SubscriptionService.sync_user_subscription_from_stripe',
        side_effect=AttributeError('get'),
    ):
        response = admin_client.post(
            f'/api/v1/admin/billing/users/{user.id}/sync-stripe',
            format='json',
            HTTP_X_FORWARDED_FOR='203.0.113.42',
        )

    assert response.status_code == 400
    payload = response.json()['data']
    assert payload['user_id'] == 'AttributeError: get'


@pytest.mark.django_db
def test_admin_can_backfill_payment_records():
    admin_user = User.objects.create_superuser(
        username='billing-admin-backfill',
        email='billing-admin-backfill@example.com',
        password='secret12345',
    )
    admin_client = APIClient()
    admin_client.force_authenticate(user=admin_user)

    with patch(
        'billing.admin_views.backfill_payment_records',
        return_value={
            'created': 2,
            'updated': 1,
            'skipped': 0,
            'processed': 3,
            'lookback_days': 30,
            'user_id': None,
            'source': 'admin_api',
        },
    ) as mock_backfill:
        response = admin_client.post(
            '/api/v1/admin/billing/payments/backfill',
            {},
            format='json',
            HTTP_X_FORWARDED_FOR='203.0.113.42',
        )

    assert response.status_code == 200
    payload = response.json()['data']
    assert payload['created'] == 2
    assert payload['updated'] == 1
    assert payload['processed'] == 3
    mock_backfill.assert_called_once()
    assert BillingAuditLog.objects.filter(
        action_type='payment_record.backfill',
        resource_type='payment_record',
        resource_id='batch',
    ).exists()


@pytest.mark.django_db
def test_admin_can_switch_user_to_another_plan(
    free_plan,
    starter_plan,
):
    admin_user = User.objects.create_superuser(
        username='billing-admin',
        email='billing-admin@example.com',
        password='secret12345',
    )
    user = User.objects.create_user(
        username='billing-switch-user',
        email='billing-switch-user@example.com',
        password='secret12345',
    )
    SubscriptionService.assign_free_plan_to_user(user)

    admin_client = APIClient()
    admin_client.force_authenticate(user=admin_user)

    response = admin_client.post(
        f'/api/v1/admin/billing/users/{user.id}/assign-plan',
        {'plan_id': starter_plan.id},
        format='json',
    )

    assert response.status_code == 200
    payload = response.json()['data']
    assert payload['created'] is False
    assert payload['replaced'] is True
    assert payload['subscription']['plan_slug'] == 'starter'
    assert payload['subscription']['status'] == 'active'

    active_subscriptions = user.subscriptions.filter(status='active')
    assert active_subscriptions.count() == 1
    assert active_subscriptions.first().plan.slug == 'starter'


@pytest.mark.django_db
@pytest.mark.parametrize(
    'subscription_status',
    ['active', 'past_due', 'trialing'],
)
def test_admin_cannot_switch_stripe_subscription_from_console(
    starter_plan,
    payment_provider,
    subscription_status,
):
    admin_user = User.objects.create_superuser(
        username='billing-admin',
        email='billing-admin@example.com',
        password='secret12345',
    )
    user = User.objects.create_user(
        username='billing-stripe-user',
        email='billing-stripe-user@example.com',
        password='secret12345',
    )
    Subscription.objects.create(
        user=user,
        plan=starter_plan,
        provider=payment_provider,
        status=subscription_status,
        auto_renew=True,
        current_period_start=timezone.now(),
        current_period_end=timezone.now() + timedelta(days=30),
    )
    UserCredits.objects.create(
        user=user,
        base_credits=starter_plan.metadata['credits_per_period'],
        bonus_credits=0,
        consumed_credits=0,
        period_start=timezone.now(),
        period_end=timezone.now() + timedelta(days=30),
        is_active=True,
    )

    admin_client = APIClient()
    admin_client.force_authenticate(user=admin_user)

    response = admin_client.post(
        f'/api/v1/admin/billing/users/{user.id}/assign-plan',
        {'plan_id': starter_plan.id},
        format='json',
    )

    assert response.status_code == 400
    assert 'Stripe subscriptions cannot be modified' in str(response.json())


@pytest.mark.django_db
def test_admin_grant_credits_writes_audit_log():
    admin_user = User.objects.create_superuser(
        username='billing-admin',
        email='billing-admin@example.com',
        password='secret12345',
    )
    user = User.objects.create_user(
        username='billing-audit-user',
        email='billing-audit-user@example.com',
        password='secret12345',
    )

    admin_client = APIClient()
    admin_client.force_authenticate(user=admin_user)

    response = admin_client.post(
        f'/api/v1/admin/billing/users/{user.id}/grant',
        {
            'amount': 12,
            'reason': 'manual_bonus',
        },
        format='json',
        HTTP_X_FORWARDED_FOR='203.0.113.10',
    )

    assert response.status_code == 201
    log = BillingAuditLog.objects.get(action_type='credits.grant')
    assert log.actor == admin_user
    assert log.actor_name == admin_user.username
    assert log.target_user == user
    assert log.target_username == user.username
    assert log.source == 'admin_api'
    assert log.ip_address == '203.0.113.10'
    assert log.context['amount'] == 12
    assert log.context['reason'] == 'manual_bonus'


@pytest.mark.django_db
def test_admin_set_subscription_writes_audit_log(
    free_plan,
    starter_plan,
):
    admin_user = User.objects.create_superuser(
        username='billing-admin',
        email='billing-admin@example.com',
        password='secret12345',
    )
    user = User.objects.create_user(
        username='billing-switch-user',
        email='billing-switch-user@example.com',
        password='secret12345',
    )
    SubscriptionService.assign_free_plan_to_user(user)

    admin_client = APIClient()
    admin_client.force_authenticate(user=admin_user)

    response = admin_client.post(
        f'/api/v1/admin/billing/users/{user.id}/assign-plan',
        {'plan_id': starter_plan.id},
        format='json',
        HTTP_X_FORWARDED_FOR='198.51.100.8',
    )

    assert response.status_code == 200
    log = BillingAuditLog.objects.get(action_type='subscription.assign')
    assert log.actor == admin_user
    assert log.target_user == user
    assert log.source == 'admin_api'
    assert log.ip_address == '198.51.100.8'
    assert log.before_data['subscription']['plan_slug'] == 'free'
    assert log.after_data['subscription']['plan_slug'] == 'starter'
    assert log.context['plan_slug'] == 'starter'


@pytest.mark.django_db
def test_admin_audit_log_list_filters_by_user():
    admin_user = User.objects.create_superuser(
        username='billing-admin',
        email='billing-admin@example.com',
        password='secret12345',
    )
    user = User.objects.create_user(
        username='billing-log-user',
        email='billing-log-user@example.com',
        password='secret12345',
    )
    BillingAuditLog.objects.create(
        actor=admin_user,
        actor_name=admin_user.username,
        target_user=user,
        target_username=user.username,
        action_type='credits.grant',
        source='admin_api',
        resource_type='credits_transaction',
        resource_id='123',
        ip_address='127.0.0.1',
        user_agent='pytest',
        before_data={},
        after_data={},
        context={'amount': 1},
        event_key='audit-test-1',
    )

    admin_client = APIClient()
    admin_client.force_authenticate(user=admin_user)

    response = admin_client.get(
        '/api/v1/admin/billing/audit-logs',
        {'user_id': user.id},
    )

    assert response.status_code == 200
    payload = response.json()['data']
    assert payload['count'] == 1
    assert payload['results'][0]['target_username'] == user.username


@pytest.mark.django_db
def test_admin_audit_log_list_filters_by_user_query_and_dates():
    admin_user = User.objects.create_superuser(
        username='billing-admin',
        email='billing-admin@example.com',
        password='secret12345',
    )
    target_user = User.objects.create_user(
        username='billing-date-user',
        email='billing-date-user@example.com',
        password='secret12345',
    )
    older_log = BillingAuditLog.objects.create(
        actor=admin_user,
        actor_name=admin_user.username,
        target_user=target_user,
        target_username=target_user.username,
        action_type='credits.grant',
        source='admin_api',
        resource_type='credits_transaction',
        resource_id='old',
        ip_address='127.0.0.1',
        user_agent='pytest',
        before_data={},
        after_data={},
        context={'amount': 1},
        event_key='audit-test-old',
    )
    newer_log = BillingAuditLog.objects.create(
        actor=admin_user,
        actor_name=admin_user.username,
        target_user=target_user,
        target_username=target_user.username,
        action_type='subscription.assign',
        source='admin_api',
        resource_type='subscription',
        resource_id='new',
        ip_address='127.0.0.1',
        user_agent='pytest',
        before_data={},
        after_data={},
        context={'plan_slug': 'starter'},
        event_key='audit-test-new',
    )
    BillingAuditLog.objects.filter(pk=older_log.pk).update(
        created_at=timezone.now() - timedelta(days=3)
    )
    BillingAuditLog.objects.filter(pk=newer_log.pk).update(
        created_at=timezone.now()
    )

    admin_client = APIClient()
    admin_client.force_authenticate(user=admin_user)

    response = admin_client.get(
        '/api/v1/admin/billing/audit-logs',
        {
            'user': 'billing-date-user',
            'action_type': 'subscription.assign',
            'start_date': (timezone.now() - timedelta(days=1)).date().isoformat(),
            'end_date': timezone.now().date().isoformat(),
        },
    )

    assert response.status_code == 200
    payload = response.json()['data']
    assert payload['count'] == 1
    assert payload['results'][0]['resource_id'] == 'new'
