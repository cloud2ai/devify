"""
Management command to fix missing EmailAlias for users

This command creates EmailAlias for all users who don't have one.
This is useful for users created through Django admin or other methods
that don't automatically create EmailAlias.
"""

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import transaction

from threadline.models import EmailAlias


class Command(BaseCommand):
    help = 'Create EmailAlias for users who are missing one'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes'
        )
        parser.add_argument(
            '--username',
            type=str,
            help='Fix specific user by username'
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        username = options.get('username')

        if username:
            users = User.objects.filter(username=username)
            if not users.exists():
                self.stdout.write(
                    self.style.ERROR(f'User "{username}" not found')
                )
                return
        else:
            users = User.objects.all()

        fixed_count = 0
        skipped_count = 0
        error_count = 0

        self.stdout.write('Checking users for missing EmailAlias...')
        self.stdout.write('')

        for user in users:
            # Check if user already has an active EmailAlias
            existing_alias = EmailAlias.objects.filter(
                user=user,
                is_active=True
            ).first()

            if existing_alias:
                skipped_count += 1
                if username:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'✓ {user.username}: Already has EmailAlias '
                            f'({existing_alias.full_email_address()})'
                        )
                    )
                continue

            # Check if username is already used as alias by another user
            alias_exists = EmailAlias.objects.filter(alias=user.username).exists()
            if alias_exists and not existing_alias:
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(
                        f'✗ {user.username}: Username already used as alias '
                        f'by another user. Please use a different alias.'
                    )
                )
                continue

            if dry_run:
                self.stdout.write(
                    self.style.WARNING(
                        f'[DRY RUN] Would create EmailAlias for {user.username}'
                    )
                )
                fixed_count += 1
            else:
                try:
                    with transaction.atomic():
                        alias = EmailAlias.objects.create(
                            user=user,
                            alias=user.username,
                            is_active=True
                        )
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'✓ {user.username}: Created EmailAlias '
                                f'({alias.full_email_address()})'
                            )
                        )
                        fixed_count += 1
                except Exception as e:
                    error_count += 1
                    self.stdout.write(
                        self.style.ERROR(
                            f'✗ {user.username}: Failed to create EmailAlias: {e}'
                        )
                    )

        self.stdout.write('')
        self.stdout.write('=' * 50)
        if dry_run:
            self.stdout.write(
                self.style.WARNING('DRY RUN - No changes made')
            )
        self.stdout.write(
            self.style.SUCCESS(
                f'Summary: {fixed_count} fixed, '
                f'{skipped_count} skipped, '
                f'{error_count} errors'
            )
        )
