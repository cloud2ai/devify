from django.core.management.base import BaseCommand

from billing.services.billing_bootstrap_service import bootstrap_local_billing


class Command(BaseCommand):
    help = 'Initialize local billing baseline data without Stripe sync'

    def add_arguments(self, parser):
        parser.add_argument(
            '--plans-config',
            type=str,
            default=None,
            help='Path to plans configuration YAML file',
        )

    def handle(self, *args, **options):
        self.stdout.write('')
        self.stdout.write('=' * 70)
        self.stdout.write(self.style.SUCCESS('BILLING BASE INITIALIZATION'))
        self.stdout.write('=' * 70)
        self.stdout.write('')

        try:
            result = bootstrap_local_billing(
                config_path=options.get('plans_config'),
                initialize_credits=True,
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"✓ Local billing initialized: {result['plans_count']} plans"
                )
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(
                    f'✗ Failed to initialize local billing: {e}'
                )
            )
            return

        self.stdout.write('')
        self.stdout.write('=' * 70)
        self.stdout.write(
            self.style.SUCCESS('BILLING BASE INITIALIZATION COMPLETED!')
        )
        self.stdout.write('=' * 70)
        self.stdout.write('')
