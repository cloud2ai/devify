import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from billing.models import Plan, PaymentProvider, PlanPrice


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
    payload = response.json()
    assert payload['billing_active'] is True
    assert 'stripe_configured' in payload

    user_client = APIClient()
    user_client.force_authenticate(user=normal_user)

    forbidden_response = user_client.get('/api/v1/admin/billing/config')

    assert forbidden_response.status_code == 403


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
    payload = response.json()
    assert payload['billing_active'] is True
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
        is_active=True,
        is_internal=False,
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
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]['slug'] == 'pro'
    assert payload[0]['stripe_price_id'] == 'price_test'
    assert payload[0]['stripe_product_id'] == 'prod_test'


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
        is_active=True,
        is_internal=False,
    )

    response = admin_client.put(
        f'/api/v1/admin/billing/plans/{plan.id}',
        {
            'name': 'Starter Plus',
            'slug': 'starter-plus',
            'description': 'Updated plan',
            'monthly_price_cents': 1999,
            'metadata': {'credits_per_period': 20, 'period_days': 45},
            'is_active': False,
            'is_internal': True,
        },
        format='json',
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload['name'] == 'Starter Plus'
    assert payload['slug'] == 'starter-plus'
    assert payload['monthly_price_cents'] == 1999
    assert payload['metadata']['credits_per_period'] == 20
    assert payload['is_active'] is False
    assert payload['is_internal'] is True
