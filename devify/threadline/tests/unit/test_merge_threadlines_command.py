"""
Unit tests for the merge_threadlines management command.
"""

from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase

from threadline.models import EmailMessage
from ..fixtures.factories import EmailMessageFactory, UserFactory


class MergeThreadlinesCommandTest(TestCase):
    def setUp(self):
        self.user = UserFactory(username="merge-command-user")

    def _create_message(self, **kwargs):
        defaults = {
            "user": self.user,
            "subject": kwargs.pop("subject", "Merge source"),
            "text_content": kwargs.pop("text_content", "Body"),
        }
        defaults.update(kwargs)
        return EmailMessageFactory(**defaults)

    def test_dry_run_rolls_back_changes(self):
        message1 = self._create_message(subject="Source one")
        message2 = self._create_message(subject="Source two")
        before_count = EmailMessage.objects.count()

        out = StringIO()
        call_command(
            "merge_threadlines",
            source_uuids=[str(message1.uuid), str(message2.uuid)],
            stdout=out,
        )

        self.assertEqual(EmailMessage.objects.count(), before_count)
        self.assertIn("Dry-run mode", out.getvalue())
        message1.refresh_from_db()
        message2.refresh_from_db()
        self.assertIsNone(message1.merged_into_id)
        self.assertIsNone(message2.merged_into_id)

    def test_apply_persists_merge(self):
        message1 = self._create_message(subject="Source one")
        message2 = self._create_message(subject="Source two")
        message1_id = message1.id
        message2_id = message2.id
        out = StringIO()
        note = "合并前已确认内容重复"

        with patch(
            "threadline.tasks.email_merge.process_email_merge.delay"
        ) as enqueue_delay:
            call_command(
                "merge_threadlines",
                source_uuids=[str(message1.uuid), str(message2.uuid)],
                apply=True,
                note=note,
                stdout=out,
            )

        # Verify the original messages are now merged
        message1.refresh_from_db()
        message2.refresh_from_db()
        self.assertIsNotNone(message1.merged_into_id)
        self.assertIsNotNone(message2.merged_into_id)

        # The canonical should be one of the source messages
        canonical_id = message1.merged_into_id
        canonical = EmailMessage.objects.get(id=canonical_id)
        # Verify the note was added to canonical's text content
        self.assertIn("[Manual merge note]", canonical.text_content)
        self.assertIn(note, canonical.text_content)
        enqueue_delay.assert_called_once()

        self.assertIn("Merge applied successfully", out.getvalue())
        self.assertIn("Workflow enqueue triggered", out.getvalue())
