from django.conf import settings
from django.core.management.base import BaseCommand

from djstripe.models import APIKey

from billing.models import Plan, PaymentProvider


class Command(BaseCommand):
    help = 'Initialize billing data (plans, providers, Stripe API keys)'

    def handle(self, *args, **options):
        self.stdout.write('Initializing billing data...')

        # Step 1: Initialize Stripe API Key in database
        self._init_stripe_api_key()

        # Step 2: Initialize payment provider
        stripe, created = PaymentProvider.objects.get_or_create(
            name='stripe',
            defaults={'display_name': 'Stripe', 'is_active': True}
        )
        if created:
            self.stdout.write(
                self.style.SUCCESS(f'Created payment provider: {stripe}')
            )

        plans = [
            {
                'name': 'Free Plan',
                'slug': 'free',
                'description': 'Perfect for trying out the service',
                'monthly_price_cents': 0,
                'metadata': {
                    'credits_per_period': 10,
                    'period_days': 30,
                    'workflow_cost_credits': 1,
                    'max_email_length': 10000,
                    'max_attachment_size_mb': 10,
                    'storage_quota_mb': 100
                }
            },
            {
                'name': 'Basic Plan',
                'slug': 'basic',
                'description': 'Ideal for individual users',
                'monthly_price_cents': 999,
                'metadata': {
                    'credits_per_period': 100,
                    'period_days': 30,
                    'workflow_cost_credits': 1,
                    'max_email_length': 50000,
                    'max_attachment_size_mb': 25,
                    'storage_quota_mb': 1024
                }
            },
            {
                'name': 'Pro Plan',
                'slug': 'pro',
                'description': 'Designed for professional users',
                'monthly_price_cents': 2999,
                'metadata': {
                    'credits_per_period': 500,
                    'period_days': 30,
                    'workflow_cost_credits': 1,
                    'max_email_length': 100000,
                    'max_attachment_size_mb': 50,
                    'storage_quota_mb': 5120
                }
            },
        ]

        for plan_data in plans:
            plan, created = Plan.objects.get_or_create(
                slug=plan_data['slug'],
                defaults=plan_data
            )
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Created plan: {plan}')
                )

        self.stdout.write(
            self.style.SUCCESS('Billing data initialized successfully')
        )

    def _init_stripe_api_key(self):
        """
        Initialize Stripe API Key in database.

        This is required for djstripe_sync_models command to work.
        Creates API key based on STRIPE_LIVE_MODE setting.
        """
        # Determine which API key to use based on mode
        is_live_mode = settings.STRIPE_LIVE_MODE
        secret_key = (
            settings.STRIPE_LIVE_SECRET_KEY
            if is_live_mode
            else settings.STRIPE_TEST_SECRET_KEY
        )
        key_name = 'Production API Key' if is_live_mode else 'Test API Key'

        # Check if secret key is configured
        if not secret_key:
            self.stdout.write(
                self.style.WARNING(
                    f'⚠️  Stripe API key not configured in environment. '
                    f'Please set STRIPE_TEST_SECRET_KEY or '
                    f'STRIPE_LIVE_SECRET_KEY'
                )
            )
            return

        # Create or get API key in database
        api_key, created = APIKey.objects.get_or_create(
            livemode=is_live_mode,
            defaults={
                'secret': secret_key,
                'name': key_name,
                'type': 'secret'
            }
        )

        if created:
            self.stdout.write(
                self.style.SUCCESS(
                    f'✅ Created Stripe API Key: {key_name} '
                    f'(ID: {api_key.id})'
                )
            )
        else:
            # Update secret if it changed
            if api_key.secret != secret_key:
                api_key.secret = secret_key
                api_key.save()
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✅ Updated Stripe API Key: {key_name}'
                    )
                )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f'⚠️  Stripe API Key already exists: {key_name}'
                    )
                )
