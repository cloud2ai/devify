"""Backfill legacy Threadline delivery settings into Relay."""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from relay.services.legacy_sync import (
    sync_all_legacy_channels,
    sync_legacy_channels_for_user,
)

User = get_user_model()


class Command(BaseCommand):
    help = (
        "Sync legacy Threadline channel settings into Relay subscriptions. "
        "Use --username to backfill one user, or --all to backfill every user."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--username",
            help="Backfill legacy channels for a single username.",
        )
        parser.add_argument(
            "--user-id",
            type=int,
            help="Backfill legacy channels for a single user ID.",
        )
        parser.add_argument(
            "--all",
            action="store_true",
            help="Backfill legacy channels for all users with legacy settings.",
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
            result = sync_all_legacy_channels()
            self.stdout.write(self.style.SUCCESS(f"Relay legacy sync: {result}"))
            return

        if user_id is not None:
            user = User.objects.filter(id=user_id).first()
        else:
            user = User.objects.filter(username=username).first()

        if not user:
            raise CommandError("Target user not found.")

        result = sync_legacy_channels_for_user(user)
        self.stdout.write(self.style.SUCCESS(f"Relay legacy sync: {result}"))
