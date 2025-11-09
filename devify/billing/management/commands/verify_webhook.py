import stripe
from django.conf import settings
from django.core.management.base import BaseCommand

from djstripe.models import WebhookEndpoint


class Command(BaseCommand):
    """
    Verify and sync webhook endpoint configuration

    Usage:
        python manage.py verify_webhook
        python manage.py verify_webhook --fix
    """
    help = 'Verify webhook endpoint configuration and sync with Stripe'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fix',
            action='store_true',
            help='Automatically fix UUID mismatch issues'
        )

    def handle(self, *args, **options):
        self.stdout.write('=' * 70)
        self.stdout.write(
            self.style.SUCCESS('Webhook Configuration Verification')
        )
        self.stdout.write('=' * 70)
        self.stdout.write('')

        stripe.api_key = (
            settings.STRIPE_LIVE_SECRET_KEY
            if settings.STRIPE_LIVE_MODE
            else settings.STRIPE_TEST_SECRET_KEY
        )

        local_webhooks = WebhookEndpoint.objects.all()
        self.stdout.write(
            f'Local webhooks in database: {local_webhooks.count()}'
        )

        for webhook in local_webhooks:
            self.stdout.write(f'  - UUID: {webhook.djstripe_uuid}')
            self.stdout.write(f'    URL: {webhook.url}')
            self.stdout.write(f'    Secret: {webhook.secret[:15]}...')
            self.stdout.write('')

        try:
            stripe_webhooks = stripe.WebhookEndpoint.list()
            self.stdout.write(
                f'Stripe webhooks: {len(stripe_webhooks.data)}'
            )

            for webhook in stripe_webhooks.data:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'  - ID: {webhook.id}'
                    )
                )
                self.stdout.write(f'    URL: {webhook.url}')
                self.stdout.write(f'    Status: {webhook.status}')
                self.stdout.write(
                    f'    Events: {", ".join(webhook.enabled_events[:3])}...'
                )

                url_parts = webhook.url.split('/')
                if 'webhook' in url_parts:
                    webhook_idx = url_parts.index('webhook')
                    if webhook_idx + 1 < len(url_parts):
                        stripe_uuid = url_parts[webhook_idx + 1]
                        self.stdout.write(f'    UUID: {stripe_uuid}')

                        local_webhook = WebhookEndpoint.objects.filter(
                            djstripe_uuid=stripe_uuid
                        ).first()

                        if local_webhook:
                            self.stdout.write(
                                self.style.SUCCESS(
                                    '    ✓ UUID matched in database'
                                )
                            )
                        else:
                            self.stdout.write(
                                self.style.ERROR(
                                    '    ✗ UUID NOT found in database'
                                )
                            )

                            if options['fix']:
                                self.fix_uuid_mismatch(
                                    webhook.id,
                                    stripe_uuid,
                                    webhook.url,
                                    webhook.secret
                                )

                self.stdout.write('')

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(
                    f'Failed to fetch Stripe webhooks: {e}'
                )
            )

        self.stdout.write('=' * 70)
        self.stdout.write(
            self.style.SUCCESS('Verification completed!')
        )
        self.stdout.write('=' * 70)

    def fix_uuid_mismatch(
        self,
        webhook_id,
        correct_uuid,
        url,
        secret
    ):
        """
        Fix UUID mismatch by updating local WebhookEndpoint
        """
        self.stdout.write('')
        self.stdout.write(
            self.style.WARNING(
                '    Fixing UUID mismatch...'
            )
        )

        local_webhook = WebhookEndpoint.objects.first()

        if local_webhook:
            local_webhook.id = webhook_id
            local_webhook.djstripe_uuid = correct_uuid
            local_webhook.url = url
            local_webhook.secret = secret
            local_webhook.save()

            self.stdout.write(
                self.style.SUCCESS(
                    f'    ✓ Updated local webhook UUID to {correct_uuid}'
                )
            )
        else:
            self.stdout.write(
                self.style.ERROR(
                    '    ✗ No local webhook to update'
                )
            )
