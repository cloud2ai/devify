from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    """
    Complete billing system initialization

    This command runs all necessary initialization steps:
    1. Initialize Stripe API keys
    2. Create billing plans
    3. Sync Stripe products
    4. Verify webhook configuration
    5. Initialize user credits

    Usage:
        python manage.py init_billing_complete
        python manage.py init_billing_complete --skip-products
        python manage.py init_billing_complete --skip-credits
    """
    help = 'Complete billing system initialization'

    def add_arguments(self, parser):
        parser.add_argument(
            '--skip-products',
            action='store_true',
            help='Skip Stripe product sync'
        )
        parser.add_argument(
            '--skip-credits',
            action='store_true',
            help='Skip user credits initialization'
        )
        parser.add_argument(
            '--skip-webhook',
            action='store_true',
            help='Skip webhook verification'
        )

    def handle(self, *args, **options):
        self.stdout.write('')
        self.stdout.write('=' * 70)
        self.stdout.write(
            self.style.SUCCESS(
                'BILLING SYSTEM COMPLETE INITIALIZATION'
            )
        )
        self.stdout.write('=' * 70)
        self.stdout.write('')

        steps = [
            ('Initialize Stripe and Plans', 'init_stripe', []),
        ]

        if not options['skip_products']:
            steps.append((
                'Sync Stripe Products',
                'sync_stripe_products',
                []
            ))

        if not options['skip_webhook']:
            steps.append((
                'Verify Webhook Configuration',
                'verify_webhook',
                []
            ))

        if not options['skip_credits']:
            steps.append((
                'Initialize User Credits',
                'init_user_credits',
                []
            ))

        total_steps = len(steps)

        for idx, (description, command, args) in enumerate(steps, 1):
            self.stdout.write(
                self.style.WARNING(
                    f'[{idx}/{total_steps}] {description}...'
                )
            )
            self.stdout.write('')

            try:
                call_command(command, *args)
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✓ {description} completed'
                    )
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f'✗ {description} failed: {e}'
                    )
                )

            self.stdout.write('')
            self.stdout.write('-' * 70)
            self.stdout.write('')

        self.stdout.write('=' * 70)
        self.stdout.write(
            self.style.SUCCESS(
                'BILLING SYSTEM INITIALIZATION COMPLETED!'
            )
        )
        self.stdout.write('=' * 70)
        self.stdout.write('')

        self.stdout.write('Next steps:')
        self.stdout.write(
            '  1. Configure webhook in Stripe Dashboard if not done'
        )
        self.stdout.write(
            '  2. Test subscription flow in frontend'
        )
        self.stdout.write(
            '  3. Monitor webhook events in logs'
        )
        self.stdout.write('')
