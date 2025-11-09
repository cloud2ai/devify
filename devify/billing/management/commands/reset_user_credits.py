from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

from billing.services.credits_service import CreditsService


class Command(BaseCommand):
    help = 'Reset credits for a specific user based on their subscription'

    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            type=str,
            help='Username to reset credits for'
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Reset credits for all users with active subscriptions'
        )

    def handle(self, *args, **options):
        username = options.get('username')
        reset_all = options.get('all', False)

        if not username and not reset_all:
            self.stdout.write(
                self.style.ERROR(
                    'Please provide either --username or --all'
                )
            )
            return

        if reset_all:
            users = User.objects.filter(
                credits__subscription__isnull=False,
                credits__subscription__status='active'
            )
            self.stdout.write(
                f'Resetting credits for {users.count()} users...'
            )

            for user in users:
                try:
                    CreditsService.reset_period_credits(user.id)
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'Reset credits for user: {user.username}'
                        )
                    )
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(
                            f'Failed to reset credits for '
                            f'{user.username}: {e}'
                        )
                    )
        else:
            try:
                user = User.objects.get(username=username)
                CreditsService.reset_period_credits(user.id)

                user_credits = user.credits.first()

                self.stdout.write(
                    self.style.SUCCESS(
                        f'Successfully reset credits for {user.username}\n'
                        f'Total Credits: {user_credits.total_credits}\n'
                        f'Available Credits: '
                        f'{user_credits.available_credits}'
                    )
                )
            except User.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'User {username} not found')
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f'Failed to reset credits: {e}'
                    )
                )
