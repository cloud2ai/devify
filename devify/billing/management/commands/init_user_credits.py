from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta

from billing.models import UserCredits, Plan


class Command(BaseCommand):
    help = 'Initialize credits for existing users'

    def handle(self, *args, **options):
        self.stdout.write('Initializing user credits...')

        try:
            free_plan = Plan.objects.get(slug='free')
            period_days = free_plan.metadata['period_days']
            base_credits = free_plan.metadata['credits_per_period']
        except Plan.DoesNotExist:
            self.stdout.write(
                self.style.WARNING(
                    'Free plan not found. '
                    'Please run init_stripe first.'
                )
            )
            return

        users = User.objects.all()
        created_count = 0

        for user in users:
            credits, created = UserCredits.objects.get_or_create(
                user=user,
                defaults={
                    'base_credits': base_credits,
                    'bonus_credits': 0,
                    'consumed_credits': 0,
                    'period_start': timezone.now(),
                    'period_end': (
                        timezone.now() + timedelta(days=period_days)
                    ),
                    'is_active': True
                }
            )

            if created:
                created_count += 1
                self.stdout.write(
                    f'Created credits for user: {user.username}'
                )

        self.stdout.write(
            self.style.SUCCESS(
                f'User credits initialized: '
                f'{created_count} new, '
                f'{users.count() - created_count} existing'
            )
        )
