#!/usr/bin/env python
"""
Setup test user for Cursor E2E tests

Usage:
    # Create/recreate user with plan
    docker exec devify-api-dev python /opt/devify/.cursor_tests/helpers/setup_test_user.py \
      --username test_billing_downgrade_user --plan pro --cleanup-first

    # Only cleanup
    docker exec devify-api-dev python /opt/devify/.cursor_tests/helpers/setup_test_user.py \
      --username test_billing_downgrade_user --cleanup-only
"""
import os
import sys
import argparse

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings.dev')
django.setup()

from django.contrib.auth.models import User
from billing.models import Plan, Subscription, UserCredits
from datetime import datetime, timedelta

FIXED_PASSWORD = "Test123456!"

PLAN_CREDITS = {
    'free': 10,
    'basic': 100,
    'pro': 500
}

def cleanup_user(username: str):
    """Delete user and all related data"""
    try:
        user = User.objects.get(username=username)
        user.delete()
        print(f"✓ Cleaned up existing user: {username}")
        return True
    except User.DoesNotExist:
        print(f"ℹ No existing user: {username}")
        return False

def create_user(username: str, plan_slug: str):
    """Create test user with specified plan"""

    # Create user
    user = User.objects.create_user(
        username=username,
        email=f"{username}@test.local",
        password=FIXED_PASSWORD
    )
    print(f"✓ Created user: {username}")

    # Create credits
    base_credits = PLAN_CREDITS.get(plan_slug, 10)
    UserCredits.objects.create(
        user=user,
        base_credits=base_credits,
        bonus_credits=0,
        consumed_credits=0
    )
    print(f"✓ Base credits: {base_credits}")

    # Create subscription if not free
    if plan_slug != 'free':
        plan = Plan.objects.get(slug=plan_slug)
        now = datetime.now()

        Subscription.objects.create(
            user=user,
            plan=plan,
            status='active',
            auto_renew=True,
            current_period_start=now,
            current_period_end=now + timedelta(days=30)
        )
        print(f"✓ Plan: {plan_slug}")
        print(f"✓ Status: active")
        print(f"✓ Auto-renew: true")
    else:
        print(f"✓ Plan: free (no subscription)")

    print(f"\n📋 Login credentials:")
    print(f"   Username: {username}")
    print(f"   Password: {FIXED_PASSWORD}")

    return user

def main():
    parser = argparse.ArgumentParser(
        description='Setup test user for Cursor E2E tests'
    )
    parser.add_argument('--username', required=True,
                       help='Fixed username (e.g., test_billing_downgrade_user)')
    parser.add_argument('--plan',
                       choices=['free', 'basic', 'pro'],
                       help='Plan slug')
    parser.add_argument('--cleanup-first', action='store_true',
                       help='Cleanup existing user before creating')
    parser.add_argument('--cleanup-only', action='store_true',
                       help='Only cleanup, do not create')

    args = parser.parse_args()

    # Cleanup if requested
    if args.cleanup_first or args.cleanup_only:
        cleanup_user(args.username)

    # Create user unless cleanup-only
    if not args.cleanup_only:
        if not args.plan:
            print("✗ --plan required when creating user")
            sys.exit(1)
        create_user(args.username, args.plan)

if __name__ == '__main__':
    main()
