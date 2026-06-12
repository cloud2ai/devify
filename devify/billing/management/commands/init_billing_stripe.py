import os
import uuid

import stripe
from django.core.management.base import BaseCommand

from djstripe.models import APIKey, WebhookEndpoint

from billing.models import Plan
from billing.services.djstripe_service import ensure_djstripe_owner_account
from billing.services.billing_bootstrap_service import bootstrap_local_billing
from billing.services.config_service import get_stripe_secret_key, get_billing_config
from billing.services.stripe_sync_service import StripePlanSyncService


class Command(BaseCommand):
    """
    Manually sync billing data to Stripe.

    This command is for repair / bootstrap use only. It does not run from the
    service entrypoint anymore.

    Usage:
        python manage.py init_billing_stripe
        python manage.py init_billing_stripe --skip-webhook
        python manage.py init_billing_stripe --skip-credits
    """
    help = 'Manually sync billing plans to Stripe'

    def add_arguments(self, parser):
        parser.add_argument(
            '--skip-webhook',
            action='store_true',
            help='Skip webhook creation'
        )
        parser.add_argument(
            '--skip-credits',
            action='store_true',
            help='Skip user credits initialization'
        )
        parser.add_argument(
            '--skip-products',
            action='store_true',
            help='Skip Stripe product/price creation'
        )
        parser.add_argument(
            '--plans-config',
            type=str,
            default=None,
            help='Path to plans configuration YAML file'
        )

    def handle(self, *args, **options):
        self.stdout.write('')
        self.stdout.write('=' * 70)
        self.stdout.write(self.style.SUCCESS('BILLING STRIPE SYNC'))
        self.stdout.write('=' * 70)
        self.stdout.write('')

        stripe_secret_key = get_stripe_secret_key()
        stripe_enabled = bool(stripe_secret_key)
        stripe.api_key = stripe_secret_key

        self.stdout.write(
            self.style.WARNING('[1/3] Initializing Local Billing Base...')
        )
        self.stdout.write('')

        try:
            self.init_stripe_api_key()
            bootstrap_local_billing(
                config_path=options.get('plans_config'),
                initialize_credits=not options['skip_credits'],
            )
            self.stdout.write(
                self.style.SUCCESS(
                    '✓ Local database initialized successfully'
                )
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(
                    f'✗ Failed to initialize local database: {e}'
                )
            )
            return

        self.stdout.write('')
        self.stdout.write('-' * 70)
        self.stdout.write('')

        if not stripe_enabled:
            self.stdout.write(
                self.style.WARNING(
                    '⊘ Stripe credentials not configured; '
                    'skipping Stripe product and webhook sync'
                )
            )
        elif not options['skip_products']:
            self.stdout.write(
                self.style.WARNING(
                    '[2/3] Creating/Updating Stripe Products & Prices...'
                )
            )
            self.stdout.write('')
            try:
                self.create_stripe_products()
                self.stdout.write(
                    self.style.SUCCESS(
                        '✓ Stripe products and prices configured'
                    )
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f'✗ Failed to create Stripe products: {e}'
                    )
                )
        else:
            self.stdout.write(
                self.style.WARNING('⊘ Skipping Stripe product creation')
            )

        self.stdout.write('')
        self.stdout.write('-' * 70)
        self.stdout.write('')

        if not stripe_enabled:
            self.stdout.write(
                self.style.WARNING('⊘ Skipping webhook configuration')
            )
        elif not options['skip_webhook']:
            self.stdout.write(
                self.style.WARNING('[3/3] Configuring Webhook...')
            )
            self.stdout.write('')
            try:
                self.create_or_update_webhook()
                self.stdout.write(
                    self.style.SUCCESS('✓ Webhook configured')
                )
            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(f'⚠ Webhook setup: {e}')
                )
        else:
            self.stdout.write(
                self.style.WARNING('⊘ Skipping webhook configuration')
            )

        self.stdout.write('')
        self.stdout.write('-' * 70)
        self.stdout.write('')

        self.stdout.write('')
        self.stdout.write('=' * 70)
        self.stdout.write(self.style.SUCCESS('BILLING STRIPE SYNC COMPLETED!'))
        self.stdout.write('=' * 70)
        self.stdout.write('')

    def init_stripe_api_key(self):
        """
        Initialize Stripe API Key in database (idempotent)
        """
        billing_config = get_billing_config()
        is_live_mode = billing_config.stripe_live_mode
        secret_key = get_stripe_secret_key()
        key_name = 'Production API Key' if is_live_mode else 'Test API Key'

        if not secret_key:
            self.stdout.write(
                self.style.WARNING(
                    f'✗ Stripe secret key not configured for '
                    f'{"live" if is_live_mode else "test"} mode'
                )
            )
            return

        existing_keys = list(
            APIKey.objects.filter(type='secret', livemode=is_live_mode)
        )

        if len(existing_keys) > 1:
            # Keep the most recently created key and remove duplicates
            existing_keys.sort(key=lambda k: k.pk, reverse=True)
            api_key = existing_keys[0]
            duplicates = existing_keys[1:]
            APIKey.objects.filter(
                pk__in=[k.pk for k in duplicates]
            ).delete()
            self.stdout.write(
                self.style.WARNING(
                    f'  ⚠ Removed {len(duplicates)} duplicate API key(s)'
                )
            )
            api_key.secret = secret_key
            api_key.save()
            created = False
        elif existing_keys:
            api_key = existing_keys[0]
            api_key.secret = secret_key
            api_key.save()
            created = False
        else:
            api_key = APIKey.objects.create(
                type='secret',
                livemode=is_live_mode,
                name=key_name,
                secret=secret_key,
            )
            created = True

        if created:
            self.stdout.write(
                self.style.SUCCESS(f'  ✓ Created Stripe API Key: {key_name}')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f'  ✓ Updated Stripe API Key: {key_name}')
            )

        ensure_djstripe_owner_account(secret_key)

    def create_stripe_products(self):
        """
        Create or update Stripe Products and Prices with idempotency.
        """
        plans = Plan.objects.filter(
            status='active',
            is_internal=False,
            allow_self_purchase=True,
        ).order_by('monthly_price_cents')
        for plan in plans:
            try:
                result = StripePlanSyncService.sync_plan(plan)
                self.stdout.write(
                    self.style.SUCCESS(
                        f'  ✓ {plan.name}: Price {result["provider_price_id"]}'
                    )
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f'  ✗ Failed to create price for {plan.name}: {e}'
                    )
                )

    def create_or_update_webhook(self):
        """
        Create or update webhook endpoint with idempotency.
        """
        domain = os.getenv('SITE_DOMAIN', 'localhost:8000')
        # Default to HTTPS for all non-localhost domains.
        # Stripe requires HTTPS for webhooks and does not follow redirects.
        _is_localhost = (
            domain.startswith('localhost')
            or domain.startswith('127.0.0.1')
            or domain.startswith('0.0.0.0')
        )
        protocol = 'http' if _is_localhost else 'https'

        existing_local = WebhookEndpoint.objects.filter(
            url__contains=domain
        ).first()

        if existing_local:
            self.stdout.write(
                self.style.SUCCESS(
                    f'  ✓ Webhook already configured for {domain}'
                )
            )
            self.stdout.write(f'    URL: {existing_local.url}')
            self.stdout.write(
                f'    UUID: {existing_local.djstripe_uuid}'
            )
            if not existing_local.url.startswith('https://') and not _is_localhost:
                self.stdout.write(
                    self.style.ERROR(
                        '  ✗ WARNING: Existing webhook uses HTTP instead of HTTPS.\n'
                        '    Stripe will not deliver to HTTP URLs in production.\n'
                        '    Run: python manage.py verify_webhook --fix\n'
                        '    Or delete the WebhookEndpoint record and re-run this command.'
                    )
                )
            return

        webhook_uuid = str(uuid.uuid4())
        webhook_url = (
            f'{protocol}://{domain}/api/billing/webhooks/'
            f'stripe/webhook/{webhook_uuid}'
        )

        try:
            billing_config = get_billing_config()
            webhook = stripe.WebhookEndpoint.create(
                url=webhook_url,
                enabled_events=[
                    'customer.subscription.created',
                    'customer.subscription.updated',
                    'customer.subscription.deleted',
                    'invoice.payment_succeeded',
                    'invoice.payment_failed',
                ],
                metadata={
                    'devify_managed': 'true',
                    'site_domain': domain
                }
            )

            WebhookEndpoint.objects.create(
                id=webhook.id,
                djstripe_uuid=webhook_uuid,
                url=webhook_url,
                secret=webhook.secret,
                enabled_events=webhook.enabled_events,
                status=webhook.status,
                livemode=billing_config.stripe_live_mode,
            )

            # Save the webhook secret to BillingConfig so it is available
            # through the admin UI and settings injection.
            billing_config.stripe_webhook_secret = webhook.secret
            billing_config.save(update_fields=['stripe_webhook_secret'])

            self.stdout.write(
                self.style.SUCCESS(f'  ✓ Webhook created: {webhook_url}')
            )

        except stripe.error.InvalidRequestError as e:
            if 'already exists' in str(e).lower():
                self.stdout.write(
                    self.style.WARNING(
                        f'  ⚠ Webhook already exists in Stripe for {domain}'
                    )
                )
            else:
                raise
