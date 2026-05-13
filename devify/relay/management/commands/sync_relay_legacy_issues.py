"""Backfill legacy Threadline Issue rows into Relay history tables."""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from relay.services.legacy_issue_sync import (
    sync_all_legacy_issues,
    sync_legacy_issues_for_user,
)

User = get_user_model()


class Command(BaseCommand):
    help = (
        "Sync legacy Threadline Issue records into Relay history tables. "
        "Use --username to backfill one user, or --all to backfill every user."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--username",
            help="Backfill legacy issues for a single username.",
        )
        parser.add_argument(
            "--user-id",
            type=int,
            help="Backfill legacy issues for a single user ID.",
        )
        parser.add_argument(
            "--all",
            action="store_true",
            help="Backfill legacy issues for all users with legacy issues.",
        )

    def handle(self, *args, **options):
        username = options.get("username")
        user_id = options.get("user_id")
        sync_all = options.get("all")

        if sum(bool(value) for value in (username, user_id, sync_all)) > 1:
            raise CommandError(
                "Use only one of --username, --user-id, or --all."
            )

        if sync_all or (not username and not user_id):
            result = sync_all_legacy_issues()
            self.stdout.write(self.style.SUCCESS(f"Relay legacy issues: {result}"))
            return

        if user_id is not None:
            user = User.objects.filter(id=user_id).first()
        else:
            user = User.objects.filter(username=username).first()

        if not user:
            raise CommandError("Target user not found.")

        result = sync_legacy_issues_for_user(user)
        self.stdout.write(self.style.SUCCESS(f"Relay legacy issues: {result}"))

