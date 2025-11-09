#!/usr/bin/env python
"""
Setup test user for Cursor E2E tests

Usage:
    Create user with local subscription only:
        docker exec devify-api-dev python \\
            /opt/devify/.cursor_tests/helpers/setup_test_user.py \\
            --username test_user --plan pro --cleanup-first

    Create user with real Stripe subscription:
        docker exec devify-api-dev python \\
            /opt/devify/.cursor_tests/helpers/setup_test_user.py \\
            --username test_user --plan pro --with-stripe \\
            --cleanup-first

    Cleanup only:
        docker exec devify-api-dev python \\
            /opt/devify/.cursor_tests/helpers/setup_test_user.py \\
            --username test_user --cleanup-only
"""
import argparse
import os
import sys
import traceback
from datetime import datetime
from datetime import timedelta

sys.path.insert(0, '/opt/devify')

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

import stripe

from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone

from djstripe.models import Customer
from djstripe.models import Subscription as DjstripeSubscription

from billing.models import PaymentProvider
from billing.models import Plan
from billing.models import Subscription
from billing.models import UserCredits

User = get_user_model()

FIXED_PASSWORD = "Test123456!"

PLAN_CREDITS = {
    'free': 5,
    'starter': 100,
    'standard': 500,
    'pro': 2000
}

def cleanup_user(username: str):
    """
    Delete user and all related data including Stripe resources

    Args:
        username: Username to cleanup

    Returns:
        bool: True if user was deleted, False if not found
    """
    try:
        user = User.objects.get(username=username)

        _cleanup_stripe_resources(user)

        user.delete()
        print(f"✓ Cleaned up existing user: {username}")
        return True
    except User.DoesNotExist:
        print(f"ℹ No existing user: {username}")
        return False


def _cleanup_stripe_resources(user):
    """
    Delete Stripe subscriptions and customer for user

    Args:
        user: Django User instance
    """
    try:
        stripe.api_key = settings.STRIPE_TEST_SECRET_KEY

        subscriptions = Subscription.objects.filter(
            user=user,
            djstripe_subscription__isnull=False
        )

        for sub in subscriptions:
            try:
                stripe.Subscription.delete(sub.djstripe_subscription.id)
                print(
                    f"✓ Canceled Stripe subscription: "
                    f"{sub.djstripe_subscription.id}"
                )
            except Exception as e:
                print(f"⚠ Failed to cancel Stripe subscription: {e}")

        djstripe_customers = Customer.objects.filter(subscriber=user)
        for customer in djstripe_customers:
            try:
                stripe.Customer.delete(customer.id)
                print(f"✓ Deleted Stripe customer: {customer.id}")
            except Exception as e:
                print(f"⚠ Failed to delete Stripe customer: {e}")

    except Exception as e:
        print(f"ℹ Stripe cleanup skipped: {e}")

def create_stripe_subscription(user, plan_slug: str):
    """
    Create real Stripe subscription for testing

    Args:
        user: Django User instance
        plan_slug: Plan slug ('starter', 'standard', or 'pro')

    Returns:
        DjstripeSubscription: Synced subscription instance or None
    """
    try:
        stripe.api_key = settings.STRIPE_TEST_SECRET_KEY

        plan = Plan.objects.get(slug=plan_slug)
        plan_price = plan.plan_prices.filter(
            provider__name='Stripe',
            interval='month'
        ).first()

        if not plan_price:
            print(f"✗ No Stripe price found for {plan_slug}")
            return None

        stripe_customer = _create_stripe_customer(user)
        if not stripe_customer:
            return None

        djstripe_customer = _sync_djstripe_customer(
            stripe_customer,
            user
        )
        if not djstripe_customer:
            return None

        payment_method_id = _attach_test_payment_method(
            stripe_customer.id
        )
        if not payment_method_id:
            return None

        stripe_subscription = _create_stripe_subscription_with_pm(
            stripe_customer.id,
            plan_price.provider_price_id,
            payment_method_id
        )
        if not stripe_subscription:
            return None

        djstripe_subscription = _sync_djstripe_subscription(
            stripe_subscription.id
        )
        if not djstripe_subscription:
            return None

        _attach_period_dates(djstripe_subscription, stripe_subscription)

        return djstripe_subscription

    except Exception as e:
        print(f"✗ Failed to create Stripe subscription: {e}")
        traceback.print_exc()
        return None


def _create_stripe_customer(user):
    """
    Create Stripe customer for user

    Args:
        user: Django User instance

    Returns:
        stripe.Customer: Created Stripe customer or None
    """
    try:
        stripe_customer = stripe.Customer.create(
            email=user.email,
            name=user.username,
            description=f"Test user: {user.username}",
            metadata={'django_user_id': user.id}
        )
        print(f"✓ Created Stripe customer: {stripe_customer.id}")
        return stripe_customer
    except Exception as e:
        print(f"✗ Failed to create Stripe customer: {e}")
        return None


def _sync_djstripe_customer(stripe_customer, user):
    """
    Sync Stripe customer to djstripe and link to user

    Args:
        stripe_customer: Stripe customer object
        user: Django User instance

    Returns:
        djstripe.Customer: Synced customer instance or None
    """
    try:
        djstripe_customer = Customer.sync_from_stripe_data(
            stripe_customer
        )
        djstripe_customer.subscriber = user
        djstripe_customer.save()
        print(f"✓ Synced djstripe customer")
        return djstripe_customer
    except Exception as e:
        print(f"✗ Failed to sync djstripe customer: {e}")
        return None


def _attach_test_payment_method(customer_id: str):
    """
    Attach test payment method to Stripe customer

    Uses Stripe official test token pm_card_visa for PCI compliance.
    Ref: https://stripe.com/docs/testing#cards

    Args:
        customer_id: Stripe customer ID

    Returns:
        str: Attached payment method ID or None
    """
    try:
        test_pm_token = 'pm_card_visa'

        attached_pm = stripe.PaymentMethod.attach(
            test_pm_token,
            customer=customer_id
        )
        attached_pm_id = attached_pm.id
        print(f"✓ Attached test payment method: {attached_pm_id}")

        stripe.Customer.modify(
            customer_id,
            invoice_settings={
                'default_payment_method': attached_pm_id
            }
        )
        print(f"✓ Set default payment method")

        return attached_pm_id
    except Exception as e:
        print(f"✗ Failed to attach payment method: {e}")
        return None


def _create_stripe_subscription_with_pm(
    customer_id: str,
    price_id: str,
    payment_method_id: str
):
    """
    Create Stripe subscription with payment method

    Args:
        customer_id: Stripe customer ID
        price_id: Stripe price ID
        payment_method_id: Stripe payment method ID

    Returns:
        stripe.Subscription: Created subscription or None
    """
    try:
        stripe_subscription = stripe.Subscription.create(
            customer=customer_id,
            items=[{'price': price_id}],
            default_payment_method=payment_method_id,
            expand=['latest_invoice', 'pending_setup_intent']
        )
        print(f"✓ Created subscription: {stripe_subscription.id}")
        return stripe_subscription
    except Exception as e:
        print(f"✗ Failed to create subscription: {e}")
        return None


def _sync_djstripe_subscription(subscription_id: str):
    """
    Sync Stripe subscription to djstripe

    Args:
        subscription_id: Stripe subscription ID

    Returns:
        DjstripeSubscription: Synced subscription or None
    """
    try:
        refreshed_stripe_sub = stripe.Subscription.retrieve(
            subscription_id
        )
        djstripe_subscription = DjstripeSubscription.sync_from_stripe_data(
            refreshed_stripe_sub
        )
        print(f"✓ Synced to djstripe: {djstripe_subscription.id}")
        return djstripe_subscription
    except Exception as e:
        print(f"✗ Failed to sync djstripe subscription: {e}")
        return None


def _attach_period_dates(djstripe_subscription, stripe_subscription):
    """
    Attach period dates from Stripe to djstripe subscription

    Args:
        djstripe_subscription: djstripe Subscription instance
        stripe_subscription: Stripe subscription object
    """
    billing_cycle_anchor = stripe_subscription.get(
        'billing_cycle_anchor'
    )
    if billing_cycle_anchor:
        period_start_ts = billing_cycle_anchor
        period_end_ts = billing_cycle_anchor + (30 * 24 * 60 * 60)

        djstripe_subscription._stripe_period_start = period_start_ts
        djstripe_subscription._stripe_period_end = period_end_ts
        print(f"✓ Period from billing_cycle_anchor: {period_start_ts}")
    else:
        print(f"⚠ No billing_cycle_anchor found")


def create_user(username: str, plan_slug: str, with_stripe: bool = False):
    """
    Create test user with specified plan

    Args:
        username: Username for test user
        plan_slug: Plan slug ('free', 'starter', 'standard', 'pro')
        with_stripe: Create real Stripe subscription if True

    Returns:
        User: Created Django User instance
    """
    user = User.objects.create_user(
        username=username,
        email=f"{username}@test.local",
        password=FIXED_PASSWORD
    )
    print(f"✓ Created user: {username}")

    now = timezone.now()
    period_start = now
    period_end = now + timedelta(days=30)

    base_credits = PLAN_CREDITS.get(plan_slug, 10)
    UserCredits.objects.create(
        user=user,
        base_credits=base_credits,
        bonus_credits=0,
        consumed_credits=0,
        period_start=period_start,
        period_end=period_end
    )
    print(f"✓ Base credits: {base_credits}")

    if plan_slug != 'free':
        _create_subscription_for_user(
            user,
            plan_slug,
            with_stripe,
            period_start,
            period_end
        )
    else:
        print(f"✓ Plan: free (no subscription)")

    print(f"\n📋 Login credentials:")
    print(f"   Username: {username}")
    print(f"   Password: {FIXED_PASSWORD}")

    return user


def _create_subscription_for_user(
    user,
    plan_slug: str,
    with_stripe: bool,
    period_start,
    period_end
):
    """
    Create subscription for user

    Args:
        user: Django User instance
        plan_slug: Plan slug
        with_stripe: Create real Stripe subscription if True
        period_start: Initial period start datetime
        period_end: Initial period end datetime
    """
    plan = Plan.objects.get(slug=plan_slug)

    provider = PaymentProvider.objects.filter(name='Stripe').first()
    if not provider:
        print("✗ Stripe payment provider not found")
        sys.exit(1)

    djstripe_subscription = None
    if with_stripe:
        print("\n🔄 Creating real Stripe subscription...")
        djstripe_subscription = create_stripe_subscription(user, plan_slug)
        if djstripe_subscription:
            period_start, period_end = _sync_stripe_period_dates(
                djstripe_subscription,
                user
            )
        else:
            print("⚠ Stripe subscription creation failed, using local dates")

    Subscription.objects.create(
        user=user,
        plan=plan,
        provider=provider,
        djstripe_subscription=djstripe_subscription,
        status='active',
        auto_renew=True,
        current_period_start=period_start,
        current_period_end=period_end
    )
    print(f"✓ Plan: {plan_slug}")
    print(f"✓ Status: active")
    print(f"✓ Auto-renew: true")
    if djstripe_subscription:
        print(f"✓ Stripe subscription ID: {djstripe_subscription.id}")


def _sync_stripe_period_dates(djstripe_subscription, user):
    """
    Sync Stripe period dates to UserCredits

    Args:
        djstripe_subscription: djstripe Subscription instance
        user: Django User instance

    Returns:
        tuple: (period_start, period_end) as timezone-aware datetimes
    """
    period_start = timezone.make_aware(
        datetime.fromtimestamp(
            djstripe_subscription._stripe_period_start
        )
    )
    period_end = timezone.make_aware(
        datetime.fromtimestamp(
            djstripe_subscription._stripe_period_end
        )
    )
    print(f"✓ Using Stripe period dates")
    print(f"  Period: {period_start} to {period_end}")

    credits = UserCredits.objects.get(user=user)
    credits.period_start = period_start
    credits.period_end = period_end
    credits.djstripe_customer = djstripe_subscription.customer
    credits.save()
    print(f"✓ Updated credits period to match Stripe")

    return period_start, period_end

def main():
    """
    Main entry point for test user setup script
    """
    parser = argparse.ArgumentParser(
        description='Setup test user for Cursor E2E tests'
    )
    parser.add_argument(
        '--username',
        required=True,
        help='Username (e.g., test_billing_downgrade_user)'
    )
    parser.add_argument(
        '--plan',
        choices=['free', 'starter', 'standard', 'pro'],
        help='Plan slug'
    )
    parser.add_argument(
        '--with-stripe',
        action='store_true',
        help='Create real Stripe subscription for full testing'
    )
    parser.add_argument(
        '--cleanup-first',
        action='store_true',
        help='Cleanup existing user before creating'
    )
    parser.add_argument(
        '--cleanup-only',
        action='store_true',
        help='Only cleanup, do not create'
    )

    args = parser.parse_args()

    if args.cleanup_first or args.cleanup_only:
        cleanup_user(args.username)

    if not args.cleanup_only:
        if not args.plan:
            print("✗ --plan required when creating user")
            sys.exit(1)
        create_user(
            args.username,
            args.plan,
            with_stripe=args.with_stripe
        )


if __name__ == '__main__':
    main()
