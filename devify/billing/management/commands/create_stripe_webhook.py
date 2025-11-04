import uuid

import stripe
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from djstripe.models import Account, WebhookEndpoint


class Command(BaseCommand):
    help = 'Create local WebhookEndpoint record from Stripe Dashboard'

    def add_arguments(self, parser):
        parser.add_argument(
            '--uuid',
            type=str,
            required=False,
            help=(
                'UUID used in webhook URL '
                '(e.g., c9b59375-58f3-4ed3-85cd-f604466177b8). '
                'If not provided, will generate a new one.'
            )
        )
        parser.add_argument(
            '--webhook-id',
            type=str,
            required=False,
            help=(
                'Stripe Webhook ID (e.g., we_1QQxxxxx). '
                'If not provided, will use the latest webhook.'
            )
        )
        parser.add_argument(
            '--list',
            action='store_true',
            help='List all webhooks from Stripe without creating records'
        )
        parser.add_argument(
            '--generate-uuid',
            action='store_true',
            help='Generate a new UUID and exit (for manual webhook setup)'
        )

    def handle(self, *args, **options):
        # Handle --generate-uuid flag
        if options['generate_uuid']:
            new_uuid = uuid.uuid4()
            self.stdout.write('')
            self.stdout.write('=' * 70)
            self.stdout.write(
                self.style.SUCCESS('Generated UUID for webhook URL:')
            )
            self.stdout.write('')
            self.stdout.write(f'  {new_uuid}')
            self.stdout.write('')
            self.stdout.write('Use this UUID in your Stripe Dashboard webhook URL:')
            self.stdout.write(
                f'  http://YOUR-DOMAIN:PORT/api/billing/webhooks/'
                f'stripe/webhook/{new_uuid}'
            )
            self.stdout.write('=' * 70)
            self.stdout.write('')
            return

        # Handle --list flag
        if options['list']:
            self.list_webhooks()
            return

        stripe.api_key = settings.STRIPE_TEST_SECRET_KEY

        # Get or generate UUID
        webhook_uuid = options.get('uuid')
        if not webhook_uuid:
            webhook_uuid = str(uuid.uuid4())
            self.stdout.write(
                self.style.WARNING(
                    f'⚠️  No UUID provided, generated new one: '
                    f'{webhook_uuid}'
                )
            )
            self.stdout.write('')

        webhook_id = options.get('webhook_id')

        # Validate UUID format
        try:
            uuid.UUID(webhook_uuid)
        except ValueError:
            raise CommandError(
                f'Invalid UUID format: {webhook_uuid}'
            )

        self.stdout.write('Fetching webhook from Stripe...')
        self.stdout.write('')

        # Fetch webhook from Stripe
        try:
            if webhook_id:
                stripe_webhook = stripe.WebhookEndpoint.retrieve(
                    webhook_id
                )
            else:
                webhooks = stripe.WebhookEndpoint.list(limit=1)
                if not webhooks.data:
                    raise CommandError(
                        'No webhook found in Stripe. '
                        'Please create one in Stripe Dashboard first.'
                    )
                stripe_webhook = webhooks.data[0]

            self.stdout.write(
                self.style.SUCCESS('✅ Fetched from Stripe:')
            )
            self.stdout.write(f'  ID: {stripe_webhook.id}')
            self.stdout.write(f'  URL: {stripe_webhook.url}')
            self.stdout.write(f'  Status: {stripe_webhook.status}')
            self.stdout.write(
                f'  Events: {len(stripe_webhook.enabled_events)}'
            )
            self.stdout.write('')

        except stripe.error.StripeError as e:
            raise CommandError(
                f'Failed to fetch webhook from Stripe: {e}'
            )

        # Verify webhook secret is configured
        if not settings.DJSTRIPE_WEBHOOK_SECRET:
            raise CommandError(
                'STRIPE_WEBHOOK_SECRET not configured. '
                'Please add it to your .env file.'
            )

        # Get Account
        account = Account.objects.filter(livemode=False).first()
        if not account:
            self.stdout.write(
                self.style.WARNING(
                    '⚠️  Warning: No test Account found, '
                    'creating webhook without account link'
                )
            )
            self.stdout.write('')

        # Create or update local webhook record
        webhook_endpoint, created = WebhookEndpoint.objects.get_or_create(
            id=stripe_webhook.id,
            defaults={
                'djstripe_uuid': uuid.UUID(webhook_uuid),
                'djstripe_owner_account': account,
                'secret': settings.DJSTRIPE_WEBHOOK_SECRET,
                'url': stripe_webhook.url,
                'enabled_events': stripe_webhook.enabled_events,
                'status': stripe_webhook.status,
                'livemode': False,
                'djstripe_tolerance': 300,
                'api_version': stripe_webhook.api_version,
            }
        )

        if created:
            self.stdout.write(
                self.style.SUCCESS(
                    '✅ Successfully created local WebhookEndpoint record'
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    'ℹ️  WebhookEndpoint already exists, skipped creation'
                )
            )

        self.stdout.write('')
        self.stdout.write('Local Database Record:')
        self.stdout.write(f'  Stripe ID: {webhook_endpoint.id}')
        self.stdout.write(
            f'  Local UUID: {webhook_endpoint.djstripe_uuid}'
        )
        self.stdout.write(f'  URL: {webhook_endpoint.url}')
        self.stdout.write(f'  Status: {webhook_endpoint.status}')
        self.stdout.write(
            f'  Events: {len(webhook_endpoint.enabled_events)}'
        )

        self.stdout.write('')
        self.stdout.write('=' * 70)
        self.stdout.write(
            self.style.SUCCESS('✅ Webhook setup complete!')
        )
        self.stdout.write('=' * 70)
        self.stdout.write('')

    def list_webhooks(self):
        """
        List all webhooks from Stripe
        """
        stripe.api_key = settings.STRIPE_TEST_SECRET_KEY

        self.stdout.write('')
        self.stdout.write('Fetching webhooks from Stripe...')
        self.stdout.write('')

        try:
            webhooks = stripe.WebhookEndpoint.list()

            if not webhooks.data:
                self.stdout.write(
                    self.style.WARNING(
                        'No webhooks found in Stripe Dashboard.'
                    )
                )
                self.stdout.write('')
                self.stdout.write(
                    'Create a webhook at: '
                    'https://dashboard.stripe.com/test/webhooks'
                )
                self.stdout.write('')
                return

            self.stdout.write('=' * 70)
            self.stdout.write('Stripe Webhook Endpoints:')
            self.stdout.write('=' * 70)

            for i, wh in enumerate(webhooks.data, 1):
                self.stdout.write(f'\nWebhook {i}:')
                self.stdout.write(f'  ID: {wh.id}')
                self.stdout.write(f'  URL: {wh.url}')
                self.stdout.write(
                    f'  Status: {wh.status} '
                    f'{"✅" if wh.status == "enabled" else "❌"}'
                )
                self.stdout.write(
                    f'  Events: {len(wh.enabled_events)} types'
                )
                self.stdout.write(f'  API Version: {wh.api_version}')

            self.stdout.write('')
            self.stdout.write('=' * 70)
            self.stdout.write(
                f'Total: {len(webhooks.data)} webhook(s) found'
            )
            self.stdout.write('=' * 70)
            self.stdout.write('')
            self.stdout.write('To create a local record, use:')
            self.stdout.write(
                '  python manage.py create_stripe_webhook '
                '--uuid <YOUR-UUID>'
            )
            self.stdout.write('')

        except stripe.error.StripeError as e:
            raise CommandError(f'Failed to list webhooks: {e}')
