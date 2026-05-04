"""
Django management command for manual threadline merge simulation.

This command lets operators preview or apply the same manual merge logic used
by the UI API. By default it runs as a dry-run and rolls back all changes.

Usage:
    # Preview a merge without persisting anything
    python manage.py merge_threadlines --source-uuids <uuid1> <uuid2>

    # Apply the merge and persist the new canonical record
    python manage.py merge_threadlines --source-uuids <uuid1> <uuid2> --apply

    # Restrict the merge to a specific user:
    # python manage.py merge_threadlines --user alice --source-uuids
    # <uuid1> <uuid2>
"""

from __future__ import annotations

import logging

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from threadline.models import EmailMessage
from threadline.serializers import EmailMessageMergeSerializer
from threadline.services import ManualMergeService, enqueue_merge_workflow

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Preview or apply a manual merge for up to 5 threadlines."

    def add_arguments(self, parser):
        parser.add_argument(
            "--source-uuids",
            nargs="+",
            required=True,
            help="UUIDs of the messages to merge (2 to 5 values).",
        )
        parser.add_argument(
            "--user",
            type=str,
            help="Restrict the merge to a specific username.",
        )
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Persist the merge instead of rolling it back.",
        )
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Print detailed source and result information.",
        )
        parser.add_argument(
            "--note",
            type=str,
            help="Optional merge note to prepend to the canonical text body.",
        )

    def handle(self, *args, **options):
        source_uuids = options["source_uuids"]
        apply_merge = options["apply"]
        verbose = options["verbose"]
        username = options.get("user")
        merge_note = options.get("note")

        serializer = EmailMessageMergeSerializer(
            data={"source_uuids": source_uuids}
        )
        if not serializer.is_valid():
            raise CommandError(serializer.errors)
        source_uuids = serializer.validated_data["source_uuids"]

        queryset = (
            EmailMessage.objects.select_related("user", "merged_into")
            .prefetch_related("attachments")
            .filter(uuid__in=source_uuids)
        )
        source_messages = list(queryset.order_by("received_at", "id"))

        if len(source_messages) != len(source_uuids):
            found_uuids = {str(message.uuid) for message in source_messages}
            missing = [
                str(uuid)
                for uuid in source_uuids
                if str(uuid) not in found_uuids
            ]
            raise CommandError(
                "One or more selected messages were not found or are not "
                f"accessible: {', '.join(missing)}"
            )

        if any(message.merged_into_id for message in source_messages):
            raise CommandError("Merged child messages cannot be merged again.")

        if username:
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist as exc:
                raise CommandError(
                    f'User "{username}" does not exist.'
                ) from exc

            mismatched = [
                str(message.uuid)
                for message in source_messages
                if message.user_id != user.id
            ]
            if mismatched:
                raise CommandError(
                    "All selected messages must belong to the requested "
                    f"user. Mismatched UUIDs: {', '.join(mismatched)}"
                )
        else:
            user = source_messages[0].user
            mismatched = [
                str(message.uuid)
                for message in source_messages
                if message.user_id != user.id
            ]
            if mismatched:
                raise CommandError(
                    "All selected messages must belong to the same user. "
                    f"Mismatched UUIDs: {', '.join(mismatched)}"
                )

        merge_service = ManualMergeService()

        self.stdout.write(
            self.style.MIGRATE_HEADING(
                f"Manual merge preview for {len(source_messages)} message(s)"
            )
        )
        for index, message in enumerate(source_messages, start=1):
            self.stdout.write(
                f"  {index}. {message.uuid} | "
                f"{message.subject or '(No Subject)'}"
            )

        canonical = None
        with transaction.atomic():
            result = merge_service.merge(
                user=user,
                source_messages=source_messages,
                merge_note=merge_note,
            )

            canonical = result.canonical_message
            self.stdout.write("")
            self.stdout.write(f"Canonical UUID: {canonical.uuid}")
            self.stdout.write(
                f"Canonical subject: {canonical.subject or '(No Subject)'}"
            )
            self.stdout.write(f"Attachment count: {result.attachment_count}")
            if verbose:
                self.stdout.write("Merged text preview:")
                preview = canonical.text_content or ""
                self.stdout.write(preview[:1200] if preview else "(empty)")

            if apply_merge:
                self.stdout.write(
                    self.style.SUCCESS(
                        "Merge applied successfully. The canonical record "
                        "and merged children remain in the database."
                    )
                )
            else:
                transaction.set_rollback(True)
                self.stdout.write(
                    self.style.WARNING(
                        "Dry-run mode: all changes were rolled back."
                    )
                )

        if apply_merge and canonical is not None:
            try:
                enqueue_merge_workflow(canonical)
            except Exception as exc:
                raise CommandError(
                    f"Merge succeeded but workflow enqueue failed: {exc}"
                ) from exc

            self.stdout.write(
                self.style.SUCCESS(
                    "Workflow enqueue triggered for the canonical record."
                )
            )
