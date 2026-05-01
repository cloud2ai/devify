"""
Tests for Threadlines API endpoints

This module contains comprehensive tests for the Threadlines API CRUD operations.
Threadlines are EmailMessage objects with their attachments.
"""

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient
from unittest.mock import patch

from threadline.models import EmailMessage, EmailAttachment, Issue
from threadline.state_machine import EmailStatus
from ..fixtures.factories import (
    EmailMessageFactory,
    EmailAttachmentFactory,
    EmailMessageWithAttachmentsFactory,
    EmailMessageWithSummaryFactory,
    UserFactory,
)


@pytest.mark.django_db
@pytest.mark.e2e
class TestThreadlinesAPI:
    """
    Test cases for Threadlines API endpoints
    """

    def test_list_threadlines_unauthenticated(self, api_client):
        """
        Test that unauthenticated users cannot access threadlines
        """
        url = reverse("threadlines-list")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_threadlines_authenticated_empty(
        self, authenticated_api_client, test_user
    ):
        """
        Test listing threadlines when user has no messages
        """
        url = reverse("threadlines-list")
        response = authenticated_api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["code"] == 200
        assert response.data["message"] == "Threadlines retrieved successfully"
        assert response.data["data"]["list"] == []
        assert response.data["data"]["pagination"]["total"] == 0

    def test_list_threadlines_authenticated_with_data(
        self, authenticated_api_client, test_user, test_email_message
    ):
        """
        Test listing threadlines when user has messages
        """
        url = reverse("threadlines-list")
        response = authenticated_api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["code"] == 200
        assert len(response.data["data"]["list"]) == 1
        assert response.data["data"]["list"][0]["id"] == test_email_message.id
        assert (
            response.data["data"]["list"][0]["subject"]
            == test_email_message.subject
        )
        assert "attachments" in response.data["data"]["list"][0]

    def test_list_threadlines_excludes_merged_children(
        self, authenticated_api_client, test_user
    ):
        """
        Test that merged child rows are hidden from the default list view.
        """
        parent = EmailMessageFactory(
            user=test_user,
            subject="Canonical thread",
        )
        child = EmailMessageFactory(
            user=test_user,
            subject="Canonical thread",
            merged_into=parent,
        )

        url = reverse("threadlines-list")
        response = authenticated_api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        ids = {item["id"] for item in response.data["data"]["list"]}
        assert parent.id in ids
        assert child.id not in ids
        parent_row = next(
            item
            for item in response.data["data"]["list"]
            if item["id"] == parent.id
        )
        assert parent_row["has_merged_children"] is True

    def test_detail_threadline_includes_merged_children(
        self, authenticated_api_client, test_user
    ):
        """
        Test that detail view exposes merged child records for canonical rows.
        """
        parent = EmailMessageFactory(
            user=test_user,
            subject="Canonical thread",
        )
        child = EmailMessageFactory(
            user=test_user,
            subject="Canonical thread",
            merged_into=parent,
            merge_reason=EmailMessage.MergeReason.TEXT_SIMILARITY.value,
        )

        url = reverse("threadlines-detail", kwargs={"uuid": parent.uuid})
        response = authenticated_api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        payload = response.data["data"]
        assert "merged_children" in payload
        assert len(payload["merged_children"]) == 1
        assert payload["merged_children"][0]["id"] == child.id
        assert payload["merged_children"][0]["merged_into"] == parent.id

    def test_detail_threadline_exposes_merged_target_metadata(
        self, authenticated_api_client, test_user
    ):
        """
        Test that merged rows expose canonical UUID metadata for UI links.
        """
        parent = EmailMessageFactory(
            user=test_user,
            subject="Canonical thread",
        )
        child = EmailMessageFactory(
            user=test_user,
            subject="Canonical thread",
            merged_into=parent,
            merge_reason=EmailMessage.MergeReason.TEXT_SIMILARITY.value,
        )

        url = reverse("threadlines-detail", kwargs={"uuid": child.uuid})
        response = authenticated_api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        payload = response.data["data"]
        assert payload["merged_into"] == parent.id
        assert payload["merged_into_uuid"] == str(parent.uuid)
        assert payload["merged_into_subject"] == parent.subject

    def test_detail_threadline_includes_issue_link_metadata(
        self, authenticated_api_client, test_user
    ):
        """
        Test that detail view exposes issue link metadata for UI display.
        """
        message = EmailMessageFactory(
            user=test_user,
            subject="Issue thread",
        )
        issue = Issue.objects.create(
            user=test_user,
            email_message=message,
            title="Issue title",
            description="Issue description",
            priority="medium",
            engine="jira",
            external_id="TEST-123",
            issue_url="https://jira.example.com/browse/TEST-123",
            metadata={"project": "TEST"},
        )

        url = reverse("threadlines-detail", kwargs={"uuid": message.uuid})
        response = authenticated_api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        payload = response.data["data"]
        assert payload["issue_external_id"] == issue.external_id
        assert payload["issue_url"] == issue.issue_url

    def test_detail_merged_child_uses_direct_issue_only(
        self, authenticated_api_client, test_user
    ):
        """
        Test that merged child detail only shows its direct issue, not cluster fallback.
        """
        parent = EmailMessageFactory(
            user=test_user,
            subject="Canonical issue thread",
        )
        child = EmailMessageFactory(
            user=test_user,
            subject="Canonical issue thread",
            merged_into=parent,
        )
        issue = Issue.objects.create(
            user=test_user,
            email_message=parent,
            title="Issue title",
            description="Issue description",
            priority="medium",
            engine="jira",
            external_id="TEST-456",
            issue_url="https://jira.example.com/browse/TEST-456",
            metadata={"project": "TEST"},
        )

        url = reverse("threadlines-detail", kwargs={"uuid": child.uuid})
        response = authenticated_api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        payload = response.data["data"]
        assert payload["issue_external_id"] is None
        assert payload["issue_url"] is None

    def test_issue_cluster_endpoint_includes_child_issue(
        self, authenticated_api_client, test_user
    ):
        """
        Test that the on-demand issue cluster endpoint exposes merged child issues.
        """
        parent = EmailMessageFactory(
            user=test_user,
            subject="Canonical issue thread",
        )
        child = EmailMessageFactory(
            user=test_user,
            subject="Canonical issue thread",
            merged_into=parent,
        )
        issue = Issue.objects.create(
            user=test_user,
            email_message=child,
            title="Issue title",
            description="Issue description",
            priority="medium",
            engine="jira",
            external_id="TEST-789",
            issue_url="https://jira.example.com/browse/TEST-789",
            metadata={"project": "TEST"},
        )

        url = reverse(
            "threadlines-issue-cluster", kwargs={"uuid": parent.uuid}
        )
        response = authenticated_api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        payload = response.data["data"]
        assert payload["issue_count"] == 1
        assert payload["node_count"] == 2
        assert any(
            node["email_uuid"] == str(child.uuid)
            and node["issue_external_id"] == issue.external_id
            and node["issue_url"] == issue.issue_url
            for node in payload["nodes"]
        )

    @patch("threadline.tasks.email_merge.process_email_merge.delay")
    def test_create_threadline_returns_failed_when_dispatch_fails(
        self,
        mock_delay,
        authenticated_api_client,
        test_user,
    ):
        """
        Test that create returns a failure when task dispatch fails.
        """
        mock_delay.side_effect = RuntimeError("broker down")

        url = reverse("threadlines-list")
        data = {
            "user_id": test_user.id,
            "message_id": "<create-failure@example.com>",
            "subject": "Dispatch failure test",
            "sender": "sender@example.com",
            "recipients": "recipient@example.com",
            "received_at": timezone.now().isoformat(),
            "text_content": "Hello world",
            "html_content": "",
        }

        response = authenticated_api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        created = EmailMessage.objects.get(
            user=test_user,
            message_id=data["message_id"],
        )
        assert created.status == EmailStatus.FAILED.value
        assert "broker down" in created.error_message
        mock_delay.assert_called_once()

    @patch("threadline.tasks.email_merge.process_email_merge.delay")
    def test_retry_merged_child_targets_canonical_when_dispatch_fails(
        self,
        mock_delay,
        authenticated_api_client,
        test_user,
    ):
        """
        Test that retrying a merged child dispatches canonical and fails cleanly.
        """
        parent = EmailMessageFactory(
            user=test_user,
            subject="Canonical thread",
            status="success",
        )
        child = EmailMessageFactory(
            user=test_user,
            subject="Canonical thread",
            merged_into=parent,
            status="fetched",
        )
        mock_delay.side_effect = RuntimeError("broker down")

        url = reverse("threadlines-retry", kwargs={"uuid": child.uuid})
        response = authenticated_api_client.post(
            url, {"force": True}, format="json"
        )

        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        parent.refresh_from_db()
        child.refresh_from_db()
        assert parent.status == EmailStatus.FAILED.value
        assert "broker down" in parent.error_message
        assert child.status == EmailStatus.FETCHED.value
        assert mock_delay.call_count == 1
        assert mock_delay.call_args.args[0] == str(parent.id)

    def test_list_threadlines_with_attachments(
        self, authenticated_api_client, test_user
    ):
        """
        Test listing threadlines with attachments
        """
        # Create message with attachments
        message = EmailMessageWithAttachmentsFactory(user=test_user)

        url = reverse("threadlines-list")
        response = authenticated_api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["data"]["list"]) == 1

        threadline = response.data["data"]["list"][0]
        assert threadline["id"] == message.id
        assert len(threadline["attachments"]) == 2

        # Verify attachment data
        for attachment in threadline["attachments"]:
            assert "id" in attachment
            assert "filename" in attachment
            assert "content_type" in attachment
            assert "file_size" in attachment

    def test_list_threadlines_includes_issue_metadata(
        self, authenticated_api_client, test_user
    ):
        """
        Test that the list view exposes issue metadata for quick links.
        """
        message = EmailMessageFactory(
            user=test_user,
            subject="Issue list thread",
        )
        issue = Issue.objects.create(
            user=test_user,
            email_message=message,
            title="Issue title",
            description="Issue description",
            priority="medium",
            engine="jira",
            external_id="TEST-LIST-123",
            issue_url="https://jira.example.com/browse/TEST-LIST-123",
            metadata={"project": "TEST"},
        )

        url = reverse("threadlines-list")
        response = authenticated_api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        row = next(
            item
            for item in response.data["data"]["list"]
            if item["id"] == message.id
        )
        assert row["issue_external_id"] == issue.external_id
        assert row["issue_url"] == issue.issue_url

    def test_list_threadlines_user_isolation(
        self, authenticated_api_client, test_user
    ):
        """
        Test that users can only see their own threadlines
        """
        # Create message for another user
        other_user = UserFactory()
        other_message = EmailMessageFactory(user=other_user)

        url = reverse("threadlines-list")
        response = authenticated_api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert (
            len(response.data["data"]["list"]) == 0
        )  # Should not see other user's messages

    def test_list_threadlines_search(
        self, authenticated_api_client, test_user
    ):
        """
        Test search functionality in threadlines list
        """
        # Create messages with different subjects
        EmailMessageFactory(
            user=test_user, subject="Important Meeting Tomorrow"
        )
        EmailMessageFactory(user=test_user, subject="Weekly Report Update")
        EmailMessageFactory(
            user=test_user, subject="Project Deadline Reminder"
        )

        url = reverse("threadlines-list")
        response = authenticated_api_client.get(url, {"search": "meeting"})

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["data"]["list"]) == 1
        assert "meeting" in response.data["data"]["list"][0]["subject"].lower()

    def test_list_threadlines_search_sender(
        self, authenticated_api_client, test_user
    ):
        """
        Test search functionality by sender
        """
        EmailMessageFactory(user=test_user, sender="john.doe@company.com")
        EmailMessageFactory(user=test_user, sender="jane.smith@company.com")

        url = reverse("threadlines-list")
        response = authenticated_api_client.get(url, {"search": "john"})

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["data"]["list"]) == 1
        assert "john" in response.data["data"]["list"][0]["sender"].lower()

    def test_list_threadlines_filter_status(
        self, authenticated_api_client, test_user
    ):
        """
        Test filtering threadlines by status
        """
        EmailMessageFactory(user=test_user, status="fetched")
        EmailMessageFactory(user=test_user, status="llm_summary_success")
        EmailMessageFactory(user=test_user, status="completed")

        url = reverse("threadlines-list")
        response = authenticated_api_client.get(url, {"status": "fetched"})

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["data"]["list"]) == 1
        assert response.data["data"]["list"][0]["status"] == "fetched"

    def test_list_threadlines_basic_list(
        self, authenticated_api_client, test_user
    ):
        """
        Test basic threadlines listing (task_id filter removed)
        """
        message1 = EmailMessageFactory(user=test_user)
        message2 = EmailMessageFactory(user=test_user)

        url = reverse("threadlines-list")
        response = authenticated_api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["data"]["list"]) >= 2

    def test_list_threadlines_ordering(
        self, authenticated_api_client, test_user
    ):
        """
        Test ordering threadlines
        """
        message1 = EmailMessageFactory(user=test_user, subject="A Message")
        message2 = EmailMessageFactory(user=test_user, subject="Z Message")

        url = reverse("threadlines-list")
        response = authenticated_api_client.get(url, {"ordering": "subject"})

        assert response.status_code == status.HTTP_200_OK
        assert response.data["data"]["list"][0]["subject"] == "A Message"
        assert response.data["data"]["list"][1]["subject"] == "Z Message"

    def test_list_threadlines_ordering_received_at(
        self, authenticated_api_client, test_user
    ):
        """
        Test ordering threadlines by received_at (default)
        """
        message1 = EmailMessageFactory(
            user=test_user, received_at="2024-01-01T10:00:00Z"
        )
        message2 = EmailMessageFactory(
            user=test_user, received_at="2024-01-02T10:00:00Z"
        )

        url = reverse("threadlines-list")
        response = authenticated_api_client.get(
            url, {"ordering": "-received_at"}
        )

        assert response.status_code == status.HTTP_200_OK
        assert (
            response.data["data"]["list"][0]["received_at"]
            == "2024-01-02T10:00:00Z"
        )
        assert (
            response.data["data"]["list"][1]["received_at"]
            == "2024-01-01T10:00:00Z"
        )

    def test_list_threadlines_pagination(
        self, authenticated_api_client, test_user
    ):
        """
        Test pagination functionality
        """
        # Create multiple messages
        EmailMessageFactory.create_batch(15, user=test_user)

        url = reverse("threadlines-list")
        response = authenticated_api_client.get(
            url, {"page_size": 10, "page": 1}
        )

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["data"]["list"]) == 10
        assert response.data["data"]["pagination"]["total"] == 15
        assert response.data["data"]["pagination"]["page"] == 1
        assert response.data["data"]["pagination"]["pageSize"] == 10

    def test_create_threadline_unauthenticated(self, api_client):
        """
        Test that unauthenticated users cannot create threadlines
        """
        url = reverse("threadlines-list")
        data = {
            "message_id": "test-123",
            "subject": "Test Subject",
            "sender": "test@example.com",
            "recipients": "recipient@example.com",
            "received_at": "2024-01-01T10:00:00Z",
            "raw_content": "Test content",
        }
        response = api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_threadline_authenticated(
        self, authenticated_api_client, test_user
    ):
        """
        Test creating a new threadline
        """
        url = reverse("threadlines-list")
        data = {
            "message_id": "new-message-123",
            "subject": "New Test Subject",
            "sender": "sender@example.com",
            "recipients": "recipient@example.com",
            "received_at": "2024-01-01T10:00:00Z",
            "raw_content": "New test content",
            "html_content": "<p>HTML content</p>",
            "text_content": "Plain text content",
        }
        response = authenticated_api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["code"] == 201
        assert response.data["message"] == "Threadline created successfully"
        assert response.data["data"]["message_id"] == "new-message-123"
        assert response.data["data"]["subject"] == "New Test Subject"
        assert "attachments" in response.data["data"]

        # Verify message was created in database
        message = EmailMessage.objects.get(id=response.data["data"]["id"])
        assert message.user == test_user
        assert message.message_id == "new-message-123"

    def test_create_threadline_duplicate_message_id(
        self, authenticated_api_client, test_user, test_email_message
    ):
        """
        Test creating threadline with duplicate message ID for same user
        """
        url = reverse("threadlines-list")
        data = {
            "message_id": test_email_message.message_id,  # Duplicate message ID
            "subject": "Duplicate Message",
            "sender": "sender@example.com",
            "recipients": "recipient@example.com",
            "received_at": "2024-01-01T10:00:00Z",
            "raw_content": "Duplicate content",
        }
        response = authenticated_api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "already exists" in str(response.data)

    def test_create_threadline_missing_required_field(
        self, authenticated_api_client, test_user
    ):
        """
        Test creating threadline with missing required field
        """
        url = reverse("threadlines-list")
        data = {
            # Missing message_id
            "subject": "Test Subject",
            "sender": "sender@example.com",
            "recipients": "recipient@example.com",
            "received_at": "2024-01-01T10:00:00Z",
            "raw_content": "Test content",
        }
        response = authenticated_api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "message_id" in str(response.data).lower()

    def test_create_threadline_for_another_user(
        self, authenticated_api_client, test_user
    ):
        """
        Test creating threadline for another user (should fail)
        """
        # Create another user
        other_user = UserFactory()

        url = reverse("threadlines-list")
        data = {
            "user_id": other_user.id,  # Try to create for another user
            "message_id": "test-123",
            "subject": "Test Subject",
            "sender": "sender@example.com",
            "recipients": "recipient@example.com",
            "received_at": "2024-01-01T10:00:00Z",
            "raw_content": "Test content",
        }
        response = authenticated_api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "yourself" in str(response.data).lower()

    def test_retrieve_threadline_unauthenticated(
        self, api_client, test_email_message
    ):
        """
        Test that unauthenticated users cannot retrieve threadlines
        """
        url = reverse(
            "threadlines-detail", kwargs={"pk": test_email_message.id}
        )
        response = api_client.get(url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_retrieve_threadline_authenticated(
        self, authenticated_api_client, test_user, test_email_message
    ):
        """
        Test retrieving a specific threadline
        """
        url = reverse(
            "threadlines-detail", kwargs={"pk": test_email_message.id}
        )
        response = authenticated_api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["code"] == 200
        assert response.data["message"] == "Threadline retrieved successfully"
        assert response.data["data"]["id"] == test_email_message.id
        assert response.data["data"]["subject"] == test_email_message.subject
        assert "attachments" in response.data["data"]

    def test_retrieve_threadline_with_attachments(
        self, authenticated_api_client, test_user
    ):
        """
        Test retrieving threadline with attachments
        """
        message = EmailMessageWithAttachmentsFactory(user=test_user)

        url = reverse("threadlines-detail", kwargs={"pk": message.id})
        response = authenticated_api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["data"]["attachments"]) == 2

        # Verify attachment details
        for attachment in response.data["data"]["attachments"]:
            assert "id" in attachment
            assert "filename" in attachment
            assert "content_type" in attachment
            assert "status_display" in attachment

    def test_retrieve_threadline_with_summary(
        self, authenticated_api_client, test_user
    ):
        """
        Test retrieving threadline with summary information
        """
        message = EmailMessageWithSummaryFactory(user=test_user)

        url = reverse("threadlines-detail", kwargs={"pk": message.id})
        response = authenticated_api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["data"]["summary_title"] == message.summary_title
        assert (
            response.data["data"]["summary_content"] == message.summary_content
        )
        assert (
            response.data["data"]["summary_priority"]
            == message.summary_priority
        )
        assert response.data["data"]["llm_content"] == message.llm_content

    def test_retrieve_threadline_other_user(
        self, authenticated_api_client, test_user
    ):
        """
        Test that users cannot retrieve other users' threadlines
        """
        # Create message for another user
        other_user = UserFactory()
        other_message = EmailMessageFactory(user=other_user)

        url = reverse("threadlines-detail", kwargs={"pk": other_message.id})
        response = authenticated_api_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data["message"] == "Threadline not found"

    def test_retrieve_threadline_not_found(
        self, authenticated_api_client, test_user
    ):
        """
        Test retrieving non-existent threadline
        """
        url = reverse("threadlines-detail", kwargs={"pk": 99999})
        response = authenticated_api_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data["message"] == "Threadline not found"

    def test_update_threadline_put(
        self, authenticated_api_client, test_user, test_email_message
    ):
        """
        Test updating threadline with PUT (full update)
        """
        url = reverse(
            "threadlines-detail", kwargs={"pk": test_email_message.id}
        )
        data = {
            "subject": "Updated Subject",
            "sender": "updated@example.com",
            "recipients": "updated_recipient@example.com",
            "raw_content": "Updated raw content",
            "html_content": "<p>Updated HTML content</p>",
            "text_content": "Updated plain text content",
            "summary_title": "Updated Summary Title",
            "summary_content": "Updated summary content",
            "summary_priority": "high",
            "llm_content": "Updated LLM content",
        }
        response = authenticated_api_client.put(url, data, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["code"] == 200
        assert response.data["message"] == "Threadline updated successfully"
        assert response.data["data"]["subject"] == "Updated Subject"
        assert (
            response.data["data"]["summary_title"] == "Updated Summary Title"
        )

        # Verify update in database
        test_email_message.refresh_from_db()
        assert test_email_message.subject == "Updated Subject"
        assert test_email_message.summary_title == "Updated Summary Title"

    def test_update_threadline_patch(
        self, authenticated_api_client, test_user, test_email_message
    ):
        """
        Test updating threadline with PATCH (partial update)
        """
        url = reverse(
            "threadlines-detail", kwargs={"pk": test_email_message.id}
        )
        data = {
            "subject": "Partially Updated Subject",
            "summary_priority": "high",
        }
        response = authenticated_api_client.patch(url, data, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["code"] == 200
        assert response.data["data"]["subject"] == "Partially Updated Subject"
        assert response.data["data"]["summary_priority"] == "high"

        # Verify only specified fields were updated
        test_email_message.refresh_from_db()
        assert test_email_message.subject == "Partially Updated Subject"
        assert test_email_message.summary_priority == "high"
        # Original fields should remain unchanged
        assert test_email_message.sender == test_email_message.sender

    def test_update_threadline_status_transition(
        self, authenticated_api_client, test_user, test_email_message
    ):
        """
        Test updating threadline with valid status transition
        """
        # Set initial status
        test_email_message.status = "fetched"
        test_email_message.save()

        url = reverse(
            "threadlines-detail", kwargs={"pk": test_email_message.id}
        )
        data = {
            "status": "ocr_processing"  # Valid transition
        }
        response = authenticated_api_client.patch(url, data, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["data"]["status"] == "ocr_processing"

        # Verify status update in database
        test_email_message.refresh_from_db()
        assert test_email_message.status == "ocr_processing"

    def test_update_threadline_invalid_status_transition(
        self, authenticated_api_client, test_user, test_email_message
    ):
        """
        Test updating threadline with invalid status transition
        """
        # Set initial status
        test_email_message.status = "fetched"
        test_email_message.save()

        url = reverse(
            "threadlines-detail", kwargs={"pk": test_email_message.id}
        )
        data = {
            "status": "completed"  # Invalid transition from 'fetched' to 'completed'
        }
        response = authenticated_api_client.patch(url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Invalid status transition" in str(response.data)

    def test_update_threadline_other_user(
        self, authenticated_api_client, test_user
    ):
        """
        Test that users cannot update other users' threadlines
        """
        # Create message for another user
        other_user = UserFactory()
        other_message = EmailMessageFactory(user=other_user)

        url = reverse("threadlines-detail", kwargs={"pk": other_message.id})
        data = {"subject": "Hacked Subject"}
        response = authenticated_api_client.put(url, data, format="json")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data["message"] == "Threadline not found"

    def test_delete_threadline(
        self, authenticated_api_client, test_user, test_email_message
    ):
        """
        Test deleting a threadline
        """
        url = reverse(
            "threadlines-detail", kwargs={"pk": test_email_message.id}
        )
        response = authenticated_api_client.delete(url)

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert response.data["code"] == 204
        assert response.data["message"] == "Threadline deleted successfully"

        # Verify message was deleted from database
        assert not EmailMessage.objects.filter(
            id=test_email_message.id
        ).exists()

    def test_delete_threadline_with_attachments(
        self, authenticated_api_client, test_user
    ):
        """
        Test deleting threadline with attachments (should cascade delete)
        """
        message = EmailMessageWithAttachmentsFactory(user=test_user)
        attachment_ids = list(message.attachments.values_list("id", flat=True))

        url = reverse("threadlines-detail", kwargs={"pk": message.id})
        response = authenticated_api_client.delete(url)

        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify message and attachments were deleted
        assert not EmailMessage.objects.filter(id=message.id).exists()
        assert not EmailAttachment.objects.filter(
            id__in=attachment_ids
        ).exists()

    def test_delete_threadline_other_user(
        self, authenticated_api_client, test_user
    ):
        """
        Test that users cannot delete other users' threadlines
        """
        # Create message for another user
        other_user = UserFactory()
        other_message = EmailMessageFactory(user=other_user)

        url = reverse("threadlines-detail", kwargs={"pk": other_message.id})
        response = authenticated_api_client.delete(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data["message"] == "Threadline not found"

        # Verify message still exists in database
        assert EmailMessage.objects.filter(id=other_message.id).exists()

    def test_delete_threadline_not_found(
        self, authenticated_api_client, test_user
    ):
        """
        Test deleting non-existent threadline
        """
        url = reverse("threadlines-detail", kwargs={"pk": 99999})
        response = authenticated_api_client.delete(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data["message"] == "Threadline not found"
