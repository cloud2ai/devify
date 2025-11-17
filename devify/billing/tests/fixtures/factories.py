"""
Factory functions for creating test data
"""

from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta


def create_payment_provider(name='stripe', is_active=True):
    """
    Create a payment provider
    """
    from billing.models import PaymentProvider

    provider, _ = PaymentProvider.objects.get_or_create(
        name=name,
        defaults={
            'is_active': is_active,
            'api_key': f'test_{name}_key',
        }
    )
    return provider


def create_billing_plan(
    slug,
    name,
    monthly_price_cents,
    credits_per_period=10,
    period_days=30,
    is_internal=False,
):
    """
    Create a billing plan
    """
    from billing.models import Plan

    plan, _ = Plan.objects.get_or_create(
        slug=slug,
        defaults={
            'name': name,
            'description': f'{name} for testing',
            'monthly_price_cents': monthly_price_cents,
            'is_internal': is_internal,
            'metadata': {
                'credits_per_period': credits_per_period,
                'period_days': period_days,
                'workflow_cost_credits': 1,
            }
        }
    )
    return plan


def create_user(username='testuser', email='test@example.com'):
    """
    Create a test user
    """
    User = get_user_model()
    user = User.objects.create_user(
        username=username,
        email=email,
        password='testpass123',
    )
    return user


def create_subscription(
    user,
    plan,
    provider,
    status='active',
    auto_renew=True,
    current_period_start=None,
    current_period_end=None,
    updated_at=None,
):
    """
    Create a subscription
    """
    from billing.models import Subscription

    if current_period_start is None:
        current_period_start = timezone.now()
    if current_period_end is None:
        current_period_end = current_period_start + timedelta(days=30)

    subscription = Subscription.objects.create(
        user=user,
        plan=plan,
        provider=provider,
        status=status,
        auto_renew=auto_renew,
        current_period_start=current_period_start,
        current_period_end=current_period_end,
    )

    if updated_at:
        subscription.updated_at = updated_at
        subscription.save()

    return subscription


def create_user_credits(
    user,
    subscription,
    base_credits=10,
    consumed_credits=0,
    period_start=None,
    period_end=None,
):
    """
    Create user credits
    """
    from billing.models import UserCredits

    if period_start is None:
        period_start = timezone.now()
    if period_end is None:
        period_end = period_start + timedelta(days=30)

    credits = UserCredits.objects.create(
        user=user,
        subscription=subscription,
        base_credits=base_credits,
        consumed_credits=consumed_credits,
        period_start=period_start,
        period_end=period_end,
        is_active=True,
    )
    return credits
