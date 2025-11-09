#!/usr/bin/env python
"""
Verify database state for test user

Usage:
    docker exec devify-api-dev python /opt/devify/.cursor_tests/helpers/verify_database.py \
      --username test_billing_downgrade_user --expect-plan pro
"""
import os
import sys
import argparse

sys.path.insert(0, '/opt/devify')

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth.models import User
from billing.models import Subscription, UserCredits

PLAN_CREDITS = {
    'free': 5,
    'starter': 10,
    'standard': 20,
    'pro': 500
}

def verify_state(username: str, expect_plan: str, expect_status: str = 'active'):
    """Verify database state"""

    # Get user
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        print(f"✗ User not found: {username}")
        sys.exit(1)

    print(f"✓ User found: {username} (id={user.id})")

    # Check subscription
    if expect_plan == 'free':
        active_sub = Subscription.objects.filter(
            user=user,
            status='active'
        ).first()

        if active_sub:
            print(f"✗ Unexpected active subscription for free plan")
            sys.exit(1)
        print(f"✓ No active subscription (Free Plan)")
    else:
        try:
            subscription = Subscription.objects.select_related('plan').get(
                user=user,
                status='active'
            )
        except Subscription.DoesNotExist:
            print(f"✗ No active subscription found")
            sys.exit(1)

        actual_plan = subscription.plan.slug
        if actual_plan != expect_plan:
            print(f"✗ Plan mismatch: expected '{expect_plan}', got '{actual_plan}'")
            sys.exit(1)

        print(f"✓ Subscription verification passed")
        print(f"  Plan: {actual_plan}")
        print(f"  Status: {subscription.status}")
        print(f"  Auto-renew: {subscription.auto_renew}")

    # Check credits
    try:
        credits = UserCredits.objects.get(user=user)
        expected_credits = PLAN_CREDITS.get(expect_plan, 10)

        if credits.base_credits != expected_credits:
            print(f"✗ Credits mismatch: expected {expected_credits}, got {credits.base_credits}")
            sys.exit(1)

        print(f"✓ Credits verification passed")
        print(f"  Base: {credits.base_credits}")
        print(f"  Consumed: {credits.consumed_credits}")
        print(f"  Available: {credits.base_credits - credits.consumed_credits}")

    except UserCredits.DoesNotExist:
        print(f"✗ UserCredits not found")
        sys.exit(1)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--username', required=True,
                       help='Test username')
    parser.add_argument('--expect-plan', required=True,
                       choices=['free', 'starter', 'standard', 'pro'],
                       help='Expected plan slug')
    parser.add_argument('--expect-status', default='active',
                       help='Expected status (default: active)')

    args = parser.parse_args()
    verify_state(args.username, args.expect_plan, args.expect_status)
