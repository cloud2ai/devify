"""
Shared pytest fixtures for billing tests
"""

import pytest
import uuid
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta


@pytest.fixture
@pytest.mark.django_db
def payment_provider():
    """
    Create a Stripe payment provider
    """
    from billing.models import PaymentProvider

    provider, _ = PaymentProvider.objects.get_or_create(
        name='stripe',
        defaults={
            'is_active': True,
        }
    )
    return provider


@pytest.fixture
@pytest.mark.django_db
def free_plan():
    """
    Create Free plan
    """
    from billing.models import Plan

    plan, _ = Plan.objects.get_or_create(
        slug='free',
        defaults={
            'name': 'Free Plan',
            'description': 'Free plan for testing',
            'monthly_price_cents': 0,
            'metadata': {
                'credits_per_period': 10,
                'period_days': 30,
                'workflow_cost_credits': 1,
            }
        }
    )
    return plan


@pytest.fixture
@pytest.mark.django_db
def starter_plan():
    """
    Create Starter plan
    """
    from billing.models import Plan

    plan, _ = Plan.objects.get_or_create(
        slug='starter',
        defaults={
            'name': 'Starter Plan',
            'description': 'Starter plan for testing',
            'monthly_price_cents': 999,
            'metadata': {
                'credits_per_period': 100,
                'period_days': 30,
                'workflow_cost_credits': 1,
            }
        }
    )
    return plan


@pytest.fixture
@pytest.mark.django_db
def test_user():
    """
    Create a test user with unique username and email
    """
    User = get_user_model()
    unique_id = str(uuid.uuid4())[:8]
    user = User.objects.create_user(
        username=f'testuser_{unique_id}',
        email=f'testuser_{unique_id}@example.com',
        password='testpass123',
    )
    return user


@pytest.fixture
@pytest.mark.django_db
def test_user_with_free_subscription(test_user, free_plan, payment_provider):
    """
    Create a test user with active Free subscription
    """
    from billing.models import Subscription, UserCredits

    subscription = Subscription.objects.create(
        user=test_user,
        plan=free_plan,
        provider=payment_provider,
        status='active',
        auto_renew=True,
        current_period_start=timezone.now(),
        current_period_end=timezone.now() + timedelta(days=30),
    )

    credits = UserCredits.objects.create(
        user=test_user,
        subscription=subscription,
        base_credits=10,
        consumed_credits=0,
        period_start=timezone.now(),
        period_end=timezone.now() + timedelta(days=30),
        is_active=True,
    )

    return test_user


@pytest.fixture
@pytest.mark.django_db
def test_user_with_starter_subscription(test_user, starter_plan, payment_provider):
    """
    Create a test user with active Starter subscription
    """
    from billing.models import Subscription, UserCredits

    subscription = Subscription.objects.create(
        user=test_user,
        plan=starter_plan,
        provider=payment_provider,
        status='active',
        auto_renew=True,
        current_period_start=timezone.now(),
        current_period_end=timezone.now() + timedelta(days=30),
    )

    credits = UserCredits.objects.create(
        user=test_user,
        subscription=subscription,
        base_credits=100,
        consumed_credits=0,
        period_start=timezone.now(),
        period_end=timezone.now() + timedelta(days=30),
        is_active=True,
    )

    return test_user


@pytest.fixture
@pytest.mark.django_db
def expired_free_subscription(test_user, free_plan, payment_provider):
    """
    Create a test user with expired Free subscription
    """
    from billing.models import Subscription, UserCredits

    past_time = timezone.now() - timedelta(days=1)
    subscription = Subscription.objects.create(
        user=test_user,
        plan=free_plan,
        provider=payment_provider,
        status='active',
        auto_renew=True,
        current_period_start=past_time - timedelta(days=30),
        current_period_end=past_time,
    )

    credits = UserCredits.objects.create(
        user=test_user,
        subscription=subscription,
        base_credits=10,
        consumed_credits=5,
        period_start=subscription.current_period_start,
        period_end=subscription.current_period_end,
        is_active=True,
    )

    return test_user


@pytest.fixture
@pytest.mark.django_db
def past_due_subscription(test_user, starter_plan, payment_provider):
    """
    Create a test user with past_due Starter subscription (8 days ago)
    """
    from billing.models import Subscription, UserCredits

    past_time = timezone.now() - timedelta(days=8)
    subscription = Subscription.objects.create(
        user=test_user,
        plan=starter_plan,
        provider=payment_provider,
        status='past_due',
        auto_renew=True,
        current_period_start=timezone.now() - timedelta(days=15),
        current_period_end=timezone.now() + timedelta(days=15),
    )

    Subscription.objects.filter(pk=subscription.pk).update(
        updated_at=past_time
    )
    subscription.refresh_from_db()

    UserCredits.objects.create(
        user=test_user,
        subscription=subscription,
        base_credits=100,
        consumed_credits=50,
        period_start=subscription.current_period_start,
        period_end=subscription.current_period_end,
        is_active=True,
    )

    return test_user
