"""
Consolidated startup initialization command.

Runs migrate, superuser creation, periodic-task registration, service
initialization, and collectstatic in a single Python process so that
Django and its heavy dependencies (litellm, langgraph, …) are loaded
exactly once instead of once per management command.
"""

import os

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Run all container startup initialization steps in a single process"

    # Each sub-command runs its own system checks; skip the redundant
    # top-level check to avoid the ~12 s overhead.
    requires_system_checks = []

    def add_arguments(self, parser):
        parser.add_argument(
            "--skip-collectstatic",
            action="store_true",
            default=False,
            help="Skip collectstatic (Celery workers do not serve static files)",
        )
        parser.add_argument(
            "--skip-superuser",
            action="store_true",
            default=False,
            help="Skip superuser creation (Celery workers do not need it)",
        )

    def handle(self, *args, **options):
        """Run every initialization step in dependency order."""
        self.stdout.write(self.style.MIGRATE_HEADING("=== devify init ==="))

        call_command("migrate", "--noinput", verbosity=1)

        if not options["skip_superuser"]:
            self._ensure_superuser()

        self._soft("register_periodic_tasks")
        self._soft("init_social_apps")
        self._soft("init_billing_base")

        if not options["skip_collectstatic"]:
            call_command("collectstatic", "--noinput", verbosity=0)

        self.stdout.write(self.style.SUCCESS("=== devify init complete ==="))

    def _soft(self, command_name, **kwargs):
        """Run a management command; warn instead of aborting on failure."""
        try:
            call_command(command_name, verbosity=0, **kwargs)
        except Exception as exc:
            self.stderr.write(
                self.style.WARNING(
                    f"{command_name} completed with warnings: {exc}"
                )
            )

    def _ensure_superuser(self):
        """Create the default superuser if it does not already exist."""
        username = os.environ.get("DJANGO_SUPERUSER_USERNAME", "admin")
        email = os.environ.get("DJANGO_SUPERUSER_EMAIL", "admin@example.com")
        password = os.environ.get(
            "DJANGO_SUPERUSER_PASSWORD", "adminpassword"
        )

        User = get_user_model()
        if User.objects.filter(username=username).exists():
            self.stdout.write(
                f'Superuser "{username}" already exists, skipping.'
            )
            return

        User.objects.create_superuser(
            username=username, email=email, password=password
        )
        self.stdout.write(
            self.style.SUCCESS(f'Superuser "{username}" created.')
        )
