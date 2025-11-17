import os
import uuid
from pathlib import Path

import stripe
import yaml
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand

from djstripe.models import APIKey, WebhookEndpoint

from billing.models import Plan, PaymentProvider, PlanPrice


class Command(BaseCommand):
    """
    Initialize Stripe billing system

    This command handles:
    1. Initialize Stripe API keys in database
    2. Create PaymentProvider (Stripe)
    3. Create billing Plans (Free, Starter, Standard, Pro)
    4. Auto-create Stripe Products and Prices (with idempotency)
    5. Auto-create Stripe Webhook (with idempotency)
    6. Initialize user credits

    Usage:
        python manage.py init_billing_stripe
        python manage.py init_billing_stripe --skip-webhook
        python manage.py init_billing_stripe --skip-credits
    """
    help = 'Initialize Stripe billing system with full automation'

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
        self.stdout.write(
            self.style.SUCCESS('STRIPE BILLING SYSTEM INITIALIZATION')
        )
        self.stdout.write('=' * 70)
        self.stdout.write('')

        stripe.api_key = (
            settings.STRIPE_LIVE_SECRET_KEY
            if settings.STRIPE_LIVE_MODE
            else settings.STRIPE_TEST_SECRET_KEY
        )

        self.stdout.write(
            self.style.WARNING('[1/4] Initializing Local Database...')
        )
        self.stdout.write('')

        try:
            plans_config = self._load_plans_config(
                options.get('plans_config')
            )
            self.init_stripe_api_key()
            self.init_payment_provider()
            self.init_plans(plans_config)
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

        if not options['skip_products']:
            self.stdout.write(
                self.style.WARNING(
                    '[2/4] Creating/Updating Stripe Products & Prices...'
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

        if not options['skip_webhook']:
            self.stdout.write(
                self.style.WARNING('[3/4] Configuring Webhook...')
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

        if not options['skip_credits']:
            self.stdout.write(
                self.style.WARNING('[4/4] Initializing User Credits...')
            )
            self.stdout.write('')
            try:
                call_command('init_user_credits')
                self.stdout.write(
                    self.style.SUCCESS('✓ User credits initialized')
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f'✗ Failed to initialize user credits: {e}'
                    )
                )
        else:
            self.stdout.write(
                self.style.WARNING('⊘ Skipping user credits initialization')
            )

        self.stdout.write('')
        self.stdout.write('=' * 70)
        self.stdout.write(
            self.style.SUCCESS('BILLING SYSTEM INITIALIZATION COMPLETED!')
        )
        self.stdout.write('=' * 70)
        self.stdout.write('')

    def init_stripe_api_key(self):
        """
        Initialize Stripe API Key in database (idempotent)
        """
        is_live_mode = settings.STRIPE_LIVE_MODE
        secret_key = (
            settings.STRIPE_LIVE_SECRET_KEY
            if is_live_mode
            else settings.STRIPE_TEST_SECRET_KEY
        )
        key_name = 'Production API Key' if is_live_mode else 'Test API Key'

        if not secret_key:
            self.stdout.write(
                self.style.ERROR(
                    f'✗ Stripe secret key not configured for '
                    f'{"live" if is_live_mode else "test"} mode'
                )
            )
            return

        api_key, created = APIKey.objects.get_or_create(
            type='secret',
            livemode=is_live_mode,
            defaults={
                'name': key_name,
                'secret': secret_key
            }
        )

        if created:
            self.stdout.write(
                self.style.SUCCESS(f'  ✓ Created Stripe API Key: {key_name}')
            )
        else:
            api_key.secret = secret_key
            api_key.save()
            self.stdout.write(
                self.style.SUCCESS(f'  ✓ Updated Stripe API Key: {key_name}')
            )

    def init_payment_provider(self):
        """
        Initialize Stripe payment provider (idempotent)
        """
        stripe_provider, created = PaymentProvider.objects.get_or_create(
            name='stripe',
            defaults={'display_name': 'Stripe', 'is_active': True}
        )
        if created:
            self.stdout.write(
                self.style.SUCCESS(
                    f'  ✓ Created payment provider: {stripe_provider}'
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'  ✓ Payment provider exists: {stripe_provider}'
                )
            )

    def _load_plans_config(self, config_path=None):
        """
        Load plans configuration from YAML file
        """
        if config_path:
            config_file = Path(config_path)
        else:
            base_path = Path(settings.BASE_DIR).parent
            config_file = base_path / 'conf' / 'billing' / 'plans.yaml'

        if not config_file.exists():
            self.stdout.write(
                self.style.ERROR(
                    f'✗ Plans config file not found: {config_file}'
                )
            )
            raise FileNotFoundError(f'Plans config not found: {config_file}')

        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        self.stdout.write(
            self.style.SUCCESS(
                f'  ✓ Loaded plans config from: {config_file}'
            )
        )
        return config

    def init_plans(self, plans_config):
        """
        Initialize billing plans from configuration (idempotent)
        """
        plans = plans_config.get('plans', [])

        for plan_data in plans:
            # Create a copy to avoid modifying original dict
            plan_data_copy = plan_data.copy()
            # Extract metadata separately as it's nested
            metadata = plan_data_copy.pop('metadata', {})
            is_internal = plan_data_copy.pop('is_internal', False)

            plan, created = Plan.objects.get_or_create(
                slug=plan_data_copy['slug'],
                defaults={
                    **plan_data_copy,
                    'metadata': metadata,
                    'is_internal': is_internal
                }
            )

            if not created:
                # Update existing plan if needed
                updated = False
                updated_fields = []

                # Check and update all fields
                for field_name, field_value in plan_data_copy.items():
                    if hasattr(plan, field_name):
                        current_value = getattr(plan, field_name)
                        if current_value != field_value:
                            setattr(plan, field_name, field_value)
                            updated = True
                            updated_fields.append(field_name)

                # Check metadata
                if plan.metadata != metadata:
                    plan.metadata = metadata
                    updated = True
                    updated_fields.append('metadata')

                # Check is_internal (important for Internal Plan updates)
                if plan.is_internal != is_internal:
                    plan.is_internal = is_internal
                    updated = True
                    updated_fields.append('is_internal')

                if updated:
                    plan.save()
                    fields_str = ', '.join(updated_fields)
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'  ✓ Updated plan: {plan} (fields: {fields_str})'
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.SUCCESS(f'  ✓ Plan exists: {plan}')
                    )
            else:
                self.stdout.write(
                    self.style.SUCCESS(f'  ✓ Created plan: {plan}')
                )

    def create_stripe_products(self):
        """
        Create or update Stripe Products and Prices with idempotency.

        Best Practice: One Product with multiple Prices.
        All subscription plans share a single "aimychats.com Subscription"
        product, with each plan as a separate price.
        """
        stripe_provider = PaymentProvider.objects.get(name='stripe')
        # Exclude free plan and internal plans (they don't need Stripe products)
        plans = Plan.objects.exclude(
            slug='free'
        ).exclude(
            is_internal=True
        ).order_by('monthly_price_cents')

        # Ensure unified product exists
        product_id = self._ensure_unified_product()

        # Create or update price for each plan
        for plan in plans:
            try:
                price_id = self._ensure_stripe_price(plan, product_id)

                PlanPrice.objects.update_or_create(
                    plan=plan,
                    provider=stripe_provider,
                    interval='month',
                    defaults={
                        'provider_product_id': product_id,
                        'provider_price_id': price_id,
                        'currency': 'USD',
                        'unit_amount_cents': plan.monthly_price_cents,
                        'is_active': True
                    }
                )

                self.stdout.write(
                    self.style.SUCCESS(
                        f'  ✓ {plan.name}: Price {price_id}'
                    )
                )

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f'  ✗ Failed to create price for {plan.name}: {e}'
                    )
                )

    def _ensure_unified_product(self):
        """
        Ensure unified Stripe Product exists (create or find existing).

        Returns:
            product_id: Stripe Product ID
        """
        # Search for existing unified product
        search_query = (
            'metadata["devify_managed"]:"true" AND '
            'metadata["devify_unified"]:"true"'
        )
        search_results = stripe.Product.search(query=search_query)

        if search_results.data:
            product = search_results.data[0]
            self.stdout.write(
                f'  → Found existing unified product: {product.id}'
            )
            return product.id

        # Create new unified product
        product = stripe.Product.create(
            name='aimychats.com Subscription',
            description='Devify subscription plans for aimychats.com',
            metadata={
                'devify_managed': 'true',
                'devify_unified': 'true'
            }
        )
        self.stdout.write(
            self.style.SUCCESS(
                f'  ✓ Created unified product: {product.id}'
            )
        )
        return product.id

    def _ensure_stripe_price(self, plan, product_id):
        """
        Ensure Stripe Price exists for a plan (create or find existing).

        Args:
            plan: Plan model instance
            product_id: Stripe Product ID

        Returns:
            price_id: Stripe Price ID
        """
        # Search for existing price by metadata
        prices = stripe.Price.list(
            product=product_id,
            active=True,
            limit=100
        )

        # Find price matching this plan
        matching_price = self._find_matching_price(
            prices.data,
            plan.slug
        )

        if matching_price:
            # Check if price amount matches
            if matching_price.unit_amount != plan.monthly_price_cents:
                # Deactivate old price and create new one
                stripe.Price.modify(matching_price.id, active=False)
                self.stdout.write(
                    f'    → Deactivated old price: {matching_price.id}'
                )
            else:
                self.stdout.write(
                    f'    → Using existing price: {matching_price.id}'
                )
                return matching_price.id

        # Create new price
        return self._create_stripe_price(plan, product_id)

    def _find_matching_price(self, prices, plan_slug):
        """
        Find price matching the plan slug in the prices list.

        Args:
            prices: List of Stripe Price objects
            plan_slug: Plan slug to match

        Returns:
            Matching price object or None
        """
        for price in prices:
            if price.metadata.get('devify_plan_slug') == plan_slug:
                return price
        return None

    def _create_stripe_price(self, plan, product_id):
        """
        Create a new Stripe Price for the given plan.

        Args:
            plan: Plan model instance
            product_id: Stripe Product ID

        Returns:
            price_id: Stripe Price ID
        """
        price = stripe.Price.create(
            product=product_id,
            unit_amount=plan.monthly_price_cents,
            currency='usd',
            recurring={'interval': 'month'},
            metadata={
                'devify_plan_slug': plan.slug,
                'devify_managed': 'true'
            }
        )
        self.stdout.write(
            f'    → Created new price: {price.id}'
        )
        return price.id

    def create_or_update_webhook(self):
        """
        Create or update webhook endpoint with idempotency.
        """
        domain = os.getenv('SITE_DOMAIN', 'localhost:8000')
        # Determine protocol based on domain
        is_https = (
            ':443' in domain or
            domain.startswith('192.168')
        )
        protocol = 'https' if is_https else 'http'

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
            return

        webhook_uuid = str(uuid.uuid4())
        webhook_url = (
            f'{protocol}://{domain}/api/billing/webhooks/'
            f'stripe/webhook/{webhook_uuid}'
        )

        try:
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
                livemode=settings.STRIPE_LIVE_MODE,
            )

            self.stdout.write(
                self.style.SUCCESS(f'  ✓ Webhook created: {webhook_url}')
            )
            self.stdout.write('')
            self.stdout.write(
                self.style.WARNING(
                    '  ⚠ IMPORTANT: Add webhook secret to .env:'
                )
            )
            self.stdout.write(f'    STRIPE_WEBHOOK_SECRET={webhook.secret}')
            self.stdout.write('')

        except stripe.error.InvalidRequestError as e:
            if 'already exists' in str(e).lower():
                self.stdout.write(
                    self.style.WARNING(
                        f'  ⚠ Webhook already exists in Stripe for {domain}'
                    )
                )
            else:
                raise
