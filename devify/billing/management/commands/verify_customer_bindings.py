from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from djstripe.models import Customer


class Command(BaseCommand):
    """
    Verify Stripe customer bindings before deployment.

    Usage:
        python manage.py verify_customer_bindings
        python manage.py verify_customer_bindings --fail-on-unbound
        python manage.py verify_customer_bindings --limit 20
    """

    help = 'Verify Stripe customer bindings'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fail-on-unbound',
            action='store_true',
            help='Exit with an error if unbound customers are found',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=20,
            help='Maximum number of unbound customers to print',
        )

    def handle(self, *args, **options):
        limit = max(1, int(options['limit'] or 20))
        unbound_customers = (
            Customer.objects.select_related('subscriber')
            .filter(subscriber__isnull=True)
            .order_by('id')
        )

        total_count = Customer.objects.count()
        unbound_count = unbound_customers.count()
        bound_count = total_count - unbound_count

        self.stdout.write('=' * 70)
        self.stdout.write(self.style.SUCCESS('Stripe Customer Binding Check'))
        self.stdout.write('=' * 70)
        self.stdout.write(f'Total customers: {total_count}')
        self.stdout.write(f'Bound customers: {bound_count}')
        self.stdout.write(f'Unbound customers: {unbound_count}')
        self.stdout.write('')

        if unbound_count:
            self.stdout.write(
                self.style.WARNING(
                    f'Unbound customers (showing up to {limit}):'
                )
            )
            for customer in unbound_customers[:limit]:
                self.stdout.write(
                    f'  - {customer.id} '
                    f'email={customer.email or ""}'
                )
            self.stdout.write('')

            if options['fail_on_unbound']:
                raise CommandError(
                    f'Found {unbound_count} unbound Stripe customers'
                )
        else:
            self.stdout.write(
                self.style.SUCCESS('No unbound Stripe customers found.')
            )

        self.stdout.write('=' * 70)
