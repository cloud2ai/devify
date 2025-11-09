import stripe
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from billing.models import PaymentProvider, Plan, PlanPrice


class Command(BaseCommand):
    help = 'Sync Stripe products to local PlanPrice records'

    def add_arguments(self, parser):
        parser.add_argument(
            '--plan',
            type=str,
            help=(
                'Plan slug (e.g., starter, standard, pro). '
                'If not provided, will process all plans.'
            )
        )
        parser.add_argument(
            '--price-id',
            type=str,
            help='Stripe Price ID (e.g., price_xxxxx)'
        )
        parser.add_argument(
            '--product-id',
            type=str,
            help=(
                'Stripe Product ID (e.g., prod_xxxxx). '
                'Optional, will be fetched from price if not provided.'
            )
        )
        parser.add_argument(
            '--interval',
            type=str,
            choices=['month', 'year'],
            default='month',
            help='Billing interval (month or year)'
        )

    def handle(self, *args, **options):
        stripe.api_key = settings.STRIPE_TEST_SECRET_KEY

        try:
            stripe_provider = PaymentProvider.objects.get(name='stripe')
        except PaymentProvider.DoesNotExist:
            raise CommandError(
                'Stripe provider not found. '
                'Please run "python manage.py init_stripe" first.'
            )

        plan_slug = options.get('plan')
        price_id = options.get('price_id')

        if plan_slug and not price_id:
            raise CommandError(
                'When specifying --plan, '
                'you must also provide --price-id'
            )

        if plan_slug:
            self.sync_single_plan(
                stripe_provider,
                plan_slug,
                price_id,
                options.get('product_id'),
                options.get('interval')
            )
        else:
            self.sync_all_plans(stripe_provider)

    def sync_single_plan(
        self,
        stripe_provider,
        plan_slug,
        price_id,
        product_id=None,
        interval='month'
    ):
        """
        Sync a single plan with specified billing interval
        """
        try:
            plan = Plan.objects.get(slug=plan_slug)
        except Plan.DoesNotExist:
            raise CommandError(f'Plan "{plan_slug}" not found')

        self.stdout.write(f'Syncing plan: {plan.name}')

        try:
            stripe_price = stripe.Price.retrieve(price_id)
        except stripe.error.StripeError as e:
            raise CommandError(
                f'Failed to fetch Stripe price: {e}'
            )

        product_id = product_id or stripe_price.product

        plan_price, created = PlanPrice.objects.update_or_create(
            plan=plan,
            provider=stripe_provider,
            interval=interval,
            defaults={
                'provider_product_id': product_id,
                'provider_price_id': price_id,
                'currency': stripe_price.currency.upper(),
                'unit_amount_cents': stripe_price.unit_amount,
                'is_active': True
            }
        )

        status = '✅ Created' if created else '✅ Updated'
        self.stdout.write(
            self.style.SUCCESS(f'{status}: {plan.name} ({interval}ly)')
        )
        self.stdout.write(f'  Price ID: {price_id}')
        self.stdout.write(f'  Product ID: {product_id}')

        amount = stripe_price.unit_amount / 100
        currency = stripe_price.currency.upper()
        self.stdout.write(f'  Amount: {currency} {amount:.2f}/{interval}')

    def sync_all_plans(self, stripe_provider):
        """
        List all Stripe prices for manual mapping
        """
        self.stdout.write('Fetching all Stripe prices...')
        self.stdout.write('')

        try:
            prices = stripe.Price.list(active=True, limit=100)
        except stripe.error.StripeError as e:
            raise CommandError(
                f'Failed to fetch Stripe prices: {e}'
            )

        if not prices.data:
            self.stdout.write(
                self.style.WARNING('No active prices found in Stripe')
            )
            return

        self.stdout.write('Available Stripe Prices:')
        self.stdout.write('=' * 70)

        for i, price in enumerate(prices.data, 1):
            product = stripe.Product.retrieve(price.product)
            self.stdout.write(f'\n{i}. {product.name}')
            self.stdout.write(f'   Product ID: {product.id}')
            self.stdout.write(f'   Price ID: {price.id}')

            amount = price.unit_amount / 100 if price.unit_amount else 0
            currency = price.currency.upper()
            interval = (
                price.recurring.interval
                if price.recurring
                else "one-time"
            )
            self.stdout.write(
                f'   Amount: {currency} {amount:.2f} / {interval}'
            )

        self.stdout.write('')
        self.stdout.write('=' * 70)
        self.stdout.write('')
        self.stdout.write('To sync a plan, use:')
        self.stdout.write(
            '  python manage.py sync_stripe_products '
            '--plan <slug> --price-id <price_id> [--interval month|year]'
        )
        self.stdout.write('')
        self.stdout.write('Examples:')
        self.stdout.write(
            '  # Sync monthly price'
        )
        self.stdout.write(
            '  python manage.py sync_stripe_products '
            '--plan basic --price-id price_monthly_xxxxx'
        )
        self.stdout.write('')
        self.stdout.write(
            '  # Sync yearly price'
        )
        self.stdout.write(
            '  python manage.py sync_stripe_products '
            '--plan basic --price-id price_yearly_xxxxx --interval year'
        )
