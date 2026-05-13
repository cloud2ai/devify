"""
Integration tests for manual email merge flows.
"""

from datetime import datetime, timezone

import pytest

from threadline.models import EmailAttachment
from threadline.services.manual_merge import ManualMergeService

from .helpers import create_threadline_via_api


@pytest.mark.django_db
@pytest.mark.integration
class TestEmailMergeIntegration:
    def test_merge_creates_canonical_message_and_links_sources(
        self, test_user
    ):
        first = create_threadline_via_api(
            test_user,
            subject="First email",
            received_at=datetime(2026, 5, 7, 8, 0, tzinfo=timezone.utc),
            text_content="First body",
        )
        second = create_threadline_via_api(
            test_user,
            subject="Second email",
            received_at=datetime(2026, 5, 7, 9, 0, tzinfo=timezone.utc),
            text_content="Second body",
        )
        EmailAttachment.objects.create(
            email_message=first,
            user=test_user,
            filename="first.pdf",
            safe_filename="first.pdf",
            content_type="application/pdf",
            file_size=1,
            file_path="/tmp/first.pdf",
            is_image=False,
        )
        EmailAttachment.objects.create(
            email_message=second,
            user=test_user,
            filename="second.jpg",
            safe_filename="second.jpg",
            content_type="image/jpeg",
            file_size=1,
            file_path="/tmp/second.jpg",
            is_image=True,
        )

        service = ManualMergeService()
        result = service.merge(
            user=test_user,
            source_messages=[first, second],
            merge_note="Merge these emails",
        )

        canonical = result.canonical_message
        assert canonical.user == test_user
        assert canonical.subject == "First email"
        assert "Merge these emails" in canonical.text_content
        assert "First body" in canonical.text_content
        assert "Second body" in canonical.text_content
        assert result.attachment_count == 2

        first.refresh_from_db()
        second.refresh_from_db()
        assert first.merged_into_id == canonical.id
        assert second.merged_into_id == canonical.id
        assert first.merge_reason == "manual"
        assert second.merge_reason == "manual"
        assert first.last_merged_at is not None
        assert second.last_merged_at is not None

        attachment_names = list(
            EmailAttachment.objects.filter(email_message=canonical)
            .order_by("id")
            .values_list("filename", flat=True)
        )
        assert attachment_names == ["first.pdf", "second.jpg"]

    def test_merge_requires_at_least_two_messages(self, test_user):
        service = ManualMergeService()
        solo = create_threadline_via_api(test_user)

        with pytest.raises(ValueError, match="At least two messages"):
            service.merge(user=test_user, source_messages=[solo])
