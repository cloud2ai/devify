"""
Tests for conservative email merge behavior.
"""

from uuid import uuid4

from django.test import TestCase
from django.utils import timezone
from django.contrib.auth.models import User
from datetime import timedelta
from unittest.mock import patch

from threadline.models import EmailMessage
from threadline.services.email_merge import EmailMergeService


class TestEmailMergeService(TestCase):
    def setUp(self):
        self.service = EmailMergeService()
        self.user = self._create_user()

    def _create_user(self, username: str | None = None) -> User:
        username = username or f"tester_{uuid4().hex[:8]}"
        return User.objects.create_user(
            username=username,
            email=f"{username}@example.com",
            password="password123",
        )

    def _create_email(
        self,
        *,
        user: User | None = None,
        received_at=None,
        **kwargs,
    ) -> EmailMessage:
        user = user or self.user
        defaults = {
            "user": user,
            "message_id": kwargs.pop("message_id", f"<{uuid4().hex}@example.com>"),
            "subject": kwargs.pop("subject", "Untitled"),
            "sender": kwargs.pop("sender", "sender@example.com"),
            "recipients": kwargs.pop("recipients", "recipient@example.com"),
            "received_at": received_at or timezone.now(),
            "text_content": kwargs.pop("text_content", ""),
            "html_content": kwargs.pop("html_content", ""),
            "summary_title": kwargs.pop("summary_title", ""),
            "summary_content": kwargs.pop("summary_content", ""),
            "summary_priority": kwargs.pop("summary_priority", ""),
            "summary_data": kwargs.pop("summary_data", {}),
            "metadata": kwargs.pop("metadata", {}),
            "llm_content": kwargs.pop("llm_content", ""),
            "status": kwargs.pop("status", "success"),
        }
        defaults.update(kwargs)
        return EmailMessage.objects.create(**defaults)

    def test_similarity_does_not_merge_when_both_scores_are_low(self):
        parent = self._create_email(
            subject="Project review",
            text_content="Alpha beta gamma delta epsilon zeta eta theta",
        )
        source = self._create_email(
            subject="Project review",
            text_content="theta and appendix with unrelated notes",
            received_at=timezone.now(),
        )

        decision = self.service.decide(source)

        assert parent.pk is not None
        assert decision.should_merge is False
        assert decision.target is None

    def test_similarity_merges_on_borderline_near_duplicate(self):
        parent = self._create_email(
            subject="Project review",
            text_content=(
                "Please review the deployment plan.\n"
                "The checklist is ready.\n"
                "We should keep the release window on Friday.\n"
                "Contact support if there is a blocker."
            ),
        )
        source = self._create_email(
            subject="Project review",
            text_content=(
                "Please review the deployment plan.\n"
                "The checklist is ready.\n"
                "The release window stays on Friday.\n"
                "Contact support if there is any blocker."
            ),
            received_at=timezone.now(),
        )

        decision = self.service.decide(source)

        assert decision.should_merge is True
        assert decision.target == parent
        assert decision.reason == EmailMessage.MergeReason.TEXT_SIMILARITY.value

    def test_similarity_merges_when_partial_ratio_is_high(self):
        parent = self._create_email(
            subject="Project review",
            text_content="Alpha beta gamma delta epsilon zeta eta theta",
        )
        source = self._create_email(
            subject="Project review",
            text_content="beta gamma delta epsilon zeta eta theta plus an appendix",
            received_at=timezone.now(),
        )

        with patch(
            "threadline.services.email_merge.fuzz.ratio", return_value=58.0
        ), patch(
            "threadline.services.email_merge.fuzz.partial_ratio",
            return_value=82.0,
        ):
            decision = self.service.decide(source)

        assert parent.pk is not None
        assert decision.should_merge is True
        assert decision.target == parent
        assert decision.reason == EmailMessage.MergeReason.TEXT_SIMILARITY.value

    def test_forward_chain_with_added_content_merges(self):
        parent = self._create_email(
            subject="Project notes",
            text_content="We should keep the old plan",
        )
        source = self._create_email(
            subject="Fwd: Project notes",
            text_content="We should keep the old plan\n\nHere is the updated proposal",
            received_at=timezone.now(),
        )

        decision = self.service.decide(source)

        assert decision.should_merge is True
        assert decision.target == parent
        assert decision.reason == EmailMessage.MergeReason.FORWARD_CHAIN.value

    def test_does_not_merge_outside_three_day_window_without_thread_relation(self):
        older = self._create_email(
            subject="Weekly digest",
            text_content="Summary A\nSummary B\nSummary C",
            received_at=timezone.now() - timedelta(days=5),
        )
        newer = self._create_email(
            subject="Weekly digest",
            text_content="Summary A\nSummary B\nSummary C\nExtra note",
            received_at=timezone.now(),
        )

        decision = self.service.decide(newer)

        assert decision.should_merge is False
        assert decision.target is None

    def test_prefers_earliest_record_within_window(self):
        older = self._create_email(
            subject="Status brief",
            text_content=(
                "Line 1\n"
                "Line 2\n"
                "Line 3\n"
                "Line 4\n"
                "Line 5\n"
                "Line 6\n"
            ),
            received_at=timezone.now() - timedelta(days=1),
        )
        newer = self._create_email(
            subject="Status brief",
            text_content="Line 1\nLine 2\nLine 3",
            received_at=timezone.now(),
        )

        decision = self.service.decide(newer)

        assert decision.should_merge is True
        assert decision.target == older

    def test_html_only_records_do_not_merge_without_text_content(self):
        parent = self._create_email(
            subject="Weekly sync",
            text_content="",
            html_content="<p>Please review the draft</p>",
        )
        source = self._create_email(
            subject="Weekly sync",
            text_content="",
            html_content="<p>Please review the draft and send feedback</p>",
            received_at=timezone.now(),
        )

        decision = self.service.decide(source)

        assert decision.should_merge is False
        assert decision.target is None

    def test_cross_user_messages_do_not_merge(self):
        parent = self._create_email(
            subject="Shared subject",
            text_content="Same text",
            raw_message_id="<shared@example.com>",
        )
        other_user = self._create_user()
        source = self._create_email(
            user=other_user,
            subject="Re: Shared subject",
            text_content="Same text\n\nExtra context",
            in_reply_to="<shared@example.com>",
            received_at=timezone.now(),
        )

        decision = self.service.decide(source)

        assert decision.should_merge is False
        assert decision.target is None

    def test_reconcile_is_idempotent_for_already_merged_records(self):
        parent = self._create_email(
            subject="Status update",
            text_content="Base text",
            raw_message_id="<status@example.com>",
        )
        child = self._create_email(
            subject="Re: Status update",
            text_content="Base text\n\nMore context",
            in_reply_to="<status@example.com>",
            merged_into=parent,
            merge_reason=EmailMessage.MergeReason.THREAD_RELATION.value,
            received_at=timezone.now(),
        )

        canonical, decision = self.service.reconcile(child)

        child.refresh_from_db()
        parent.refresh_from_db()

        assert canonical.pk == parent.pk
        assert decision.should_merge is True
        assert decision.target == parent
        assert parent.text_content == "Base text"
        assert child.merged_into_id == parent.id

    def test_resolve_canonical_follows_merge_chain(self):
        parent = self._create_email(
            subject="Chain root",
            text_content="Root text",
        )
        child = self._create_email(
            subject="Re: Chain root",
            text_content="Root text\n\nExtra context",
            merged_into=parent,
            merge_reason=EmailMessage.MergeReason.TEXT_SIMILARITY.value,
        )

        resolved = self.service.resolve_canonical(child)

        assert resolved.pk == parent.pk
