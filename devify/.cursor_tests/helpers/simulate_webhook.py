#!/usr/bin/env python
"""
Simulate Stripe webhook events for testing

This script directly calls webhook handlers to simulate Stripe events
without requiring real Stripe API calls or Stripe CLI.

Usage:
    Simulate payment failure:
        docker exec devify-api-dev python \\
            /opt/devify/.cursor_tests/helpers/simulate_webhook.py \\
            --username test_user --event payment_failed

    Simulate payment success:
        docker exec devify-api-dev python \\
            /opt/devify/.cursor_tests/helpers/simulate_webhook.py \\
            --username test_user --event payment_succeeded
"""
import argparse
import json
import os
import sys
from datetime import datetime

sys.path.insert(0, '/opt/devify')

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.utils import timezone

from djstripe.models import Event

from billing.models import Subscription
from billing.webhooks import handle_payment_failed
from billing.webhooks import handle_payment_succeeded

User = get_user_model()


def simulate_payment_failed(username: str):
    """
    Simulate invoice.payment_failed event

    Args:
        username: Username to simulate failure for

    Returns:
        bool: True if successful
    """
    try:
        user = User.objects.get(username=username)
        subscription = Subscription.objects.filter(
            user=user,
            djstripe_subscription__isnull=False,
            status='active'
        ).first()

        if not subscription:
            print(f"✗ No active subscription found for {username}")
            return False

        djstripe_sub = subscription.djstripe_subscription
        customer_id = djstripe_sub.customer.id

        print(f"ℹ Simulating payment failure for:")
        print(f"  User: {username}")
        print(f"  Customer: {customer_id}")
        print(f"  Subscription: {djstripe_sub.id}")

        event_data = {
            "id": f"evt_test_{int(datetime.now().timestamp())}",
            "object": "event",
            "type": "invoice.payment_failed",
            "data": {
                "object": {
                    "id": f"in_test_{int(datetime.now().timestamp())}",
                    "object": "invoice",
                    "customer": customer_id,
                    "subscription": djstripe_sub.id,
                    "amount_due": 999,
                    "amount_paid": 0,
                    "attempt_count": 1,
                    "last_payment_error": {
                        "message": "Your card was declined",
                        "code": "card_declined"
                    },
                    "status": "open"
                }
            }
        }

        event, created = Event.objects.get_or_create(
            id=event_data['id'],
            defaults={
                'type': event_data['type'],
                'data': event_data['data'],
                'livemode': False
            }
        )

        print(f"✓ Created mock event: {event.id}")
        print(f"\n🔄 Calling webhook handler...")

        handle_payment_failed(
            sender=None,
            event=event
        )

        print(f"\n✅ Webhook simulation complete!")
        print(f"\nExpected results:")
        print(f"  - Subscription status → past_due")
        print(f"  - Email notification sent")
        print(f"  - Logs recorded")

        return True

    except Exception as e:
        print(f"✗ Failed to simulate payment failure: {e}")
        import traceback
        traceback.print_exc()
        return False


def simulate_payment_succeeded(username: str):
    """
    Simulate invoice.payment_succeeded event

    Args:
        username: Username to simulate success for

    Returns:
        bool: True if successful
    """
    try:
        user = User.objects.get(username=username)
        subscription = Subscription.objects.filter(
            user=user,
            djstripe_subscription__isnull=False,
            status='past_due'
        ).first()

        if not subscription:
            print(f"✗ No past_due subscription found for {username}")
            print(f"ℹ Run payment_failed simulation first")
            return False

        djstripe_sub = subscription.djstripe_subscription
        customer_id = djstripe_sub.customer.id

        print(f"ℹ Simulating payment success for:")
        print(f"  User: {username}")
        print(f"  Customer: {customer_id}")
        print(f"  Subscription: {djstripe_sub.id}")

        event_data = {
            "id": f"evt_test_{int(datetime.now().timestamp())}",
            "object": "event",
            "type": "invoice.payment_succeeded",
            "data": {
                "object": {
                    "id": f"in_test_{int(datetime.now().timestamp())}",
                    "object": "invoice",
                    "customer": customer_id,
                    "subscription": djstripe_sub.id,
                    "amount_due": 999,
                    "amount_paid": 999,
                    "status": "paid"
                }
            }
        }

        event, created = Event.objects.get_or_create(
            id=event_data['id'],
            defaults={
                'type': event_data['type'],
                'data': event_data['data'],
                'livemode': False
            }
        )

        print(f"✓ Created mock event: {event.id}")
        print(f"\n🔄 Calling webhook handler...")

        handle_payment_succeeded(
            sender=None,
            event=event
        )

        print(f"\n✅ Webhook simulation complete!")
        print(f"\nExpected results:")
        print(f"  - Subscription status → active")
        print(f"  - Recovery email notification sent")
        print(f"  - Logs recorded")

        return True

    except Exception as e:
        print(f"✗ Failed to simulate payment success: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """
    Main entry point for webhook simulation script
    """
    parser = argparse.ArgumentParser(
        description='Simulate Stripe webhook events for testing'
    )
    parser.add_argument(
        '--username',
        required=True,
        help='Username to simulate event for'
    )
    parser.add_argument(
        '--event',
        required=True,
        choices=['payment_failed', 'payment_succeeded'],
        help='Webhook event to simulate'
    )

    args = parser.parse_args()

    if args.event == 'payment_failed':
        success = simulate_payment_failed(args.username)
    elif args.event == 'payment_succeeded':
        success = simulate_payment_succeeded(args.username)
    else:
        print(f"✗ Unknown event: {args.event}")
        sys.exit(1)

    if not success:
        sys.exit(1)


if __name__ == '__main__':
    main()
