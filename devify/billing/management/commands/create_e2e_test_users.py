from datetime import datetime, timedelta

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone

from billing.models import PaymentProvider, Plan, Subscription, UserCredits


E2E_USERS = [
    {
        "username": "e2e-free",
        "email": "e2e-free@devify.test",
        "password": "e2e-test-password",
        "plan_slug": "free",
    },
    {
        "username": "e2e-starter",
        "email": "e2e-starter@devify.test",
        "password": "e2e-test-password",
        "plan_slug": "starter",
    },
    {
        "username": "e2e-standard",
        "email": "e2e-standard@devify.test",
        "password": "e2e-test-password",
        "plan_slug": "standard",
    },
    {
        "username": "e2e-pro",
        "email": "e2e-pro@devify.test",
        "password": "e2e-test-password",
        "plan_slug": "pro",
    },
    {
        "username": "e2e-internal",
        "email": "e2e-internal@devify.test",
        "password": "e2e-test-password",
        "plan_slug": "internal",
    },
    {
        "username": "e2e-admin",
        "email": "e2e-admin@devify.test",
        "password": "e2e-test-password",
        "plan_slug": "free",
        "is_superuser": True,
        "is_staff": True,
    },
]


class Command(BaseCommand):
    help = "Create or reset E2E test users for Playwright browser tests"

    def handle(self, **options):
        for spec in E2E_USERS:
            user, created = User.objects.update_or_create(
                username=spec["username"],
                defaults={
                    "email": spec["email"],
                    "is_superuser": spec.get("is_superuser", False),
                    "is_staff": spec.get("is_staff", False),
                },
            )
            user.set_password(spec["password"])
            user.save()

            plan = Plan.objects.filter(slug=spec["plan_slug"]).first()
            if not plan:
                self.stderr.write(f"Plan slug '{spec['plan_slug']}' not found — skipping subscription for {spec['username']}")
                continue

            # Deactivate any existing active subscriptions for this user
            Subscription.objects.filter(user=user, status="active").update(
                status="canceled"
            )

            # Look up PaymentProvider
            provider_name = (
                "platform" if spec["plan_slug"] in ("free", "internal")
                else "stripe"
            )
            payment_provider = PaymentProvider.objects.filter(
                name=provider_name
            ).first()
            if not payment_provider:
                self.stderr.write(
                    f"PaymentProvider '{provider_name}' not found — "
                    f"skipping subscription for {spec['username']}"
                )
                continue

            # Create new subscription
            now = timezone.now()
            Subscription.objects.create(
                user=user,
                plan=plan,
                status="active",
                provider=payment_provider,
                current_period_start=now,
                current_period_end=now + timedelta(days=30),
                auto_renew=True,
            )

            # Reset credits
            credits, _ = UserCredits.objects.update_or_create(
                user=user,
                defaults={
                    "base_credits": plan.metadata.get("credits_per_period", 10),
                    "bonus_credits": 0,
                    "consumed_credits": 0,
                    "period_start": now,
                    "period_end": now + timedelta(days=30),
                    "is_active": True,
                },
            )

            verb = "Created" if created else "Updated"
            self.stdout.write(f"{verb} {spec['username']} ({spec['email']}) with plan '{spec['plan_slug']}'")
