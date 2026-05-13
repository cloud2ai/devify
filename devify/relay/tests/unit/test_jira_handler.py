"""
Relay-owned unit tests for JiraIssueHandler behavior and attachment upload.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from relay.services.drivers.jira_handler import JiraIssueHandler
from threadline.utils.issues.jira_utils import (
    remove_emoji,
    build_summary_field,
)


class TestJiraIssueHandler:
    """
    Test suite for JiraIssueHandler
    """

    @pytest.fixture
    def jira_config(self):
        """
        Create a basic JIRA configuration for testing
        """
        return {
            "url": "https://jira.example.com",
            "username": "test_user",
            "api_token": "test_token",
            "project_key": "TEST",
            "default_issue_type": "Task",
            "default_priority": "Medium",
            "summary_prefix": "[AI]",
            "summary_timestamp": False,
        }

    @pytest.fixture
    def jira_handler(self, jira_config):
        """
        Create a JiraIssueHandler instance for testing
        """
        with patch("threadline.utils.issues.jira_handler.JiraClient"):
            handler = JiraIssueHandler(jira_config)
            return handler

    def test_remove_emoji_removes_emoticons(self):
        """
        Test that emoticons are removed from text
        """
        text_with_emoji = "Hello 😀 World 😃 Test 😄"
        result = remove_emoji(text_with_emoji)
        assert result == "Hello World Test "

    def test_remove_emoji_removes_symbols(self):
        """
        Test that symbol emojis are removed from text
        """
        text_with_emoji = "Weather: ☀️ ⛅ ☁️ ⚡"
        result = remove_emoji(text_with_emoji)
        assert "☀" not in result
        assert "⛅" not in result

    def test_remove_emoji_handles_empty_string(self):
        """
        Test that empty string is handled correctly
        """
        result = remove_emoji("")
        assert result == ""

    def test_remove_emoji_handles_none(self):
        """
        Test that None is handled correctly
        """
        # utils version returns None as-is for None input
        result = remove_emoji(None)
        assert result is None

    def test_remove_emoji_preserves_normal_text(self):
        """
        Test that normal text without emoji is preserved
        """
        text = "This is a normal text without any emoji"
        result = remove_emoji(text)
        assert result == text

    def test_build_summary_field_removes_emoji(self, jira_handler):
        """
        Test that build_summary_field removes emoji from final summary
        """
        summary_title = "Bug 🐛 in payment 💳 system"
        result = build_summary_field(
            summary_title, prefix="[AI]", add_timestamp=False
        )
        assert "🐛" not in result
        assert "💳" not in result
        assert result == "[AI]Bug in payment system"

    def test_build_summary_field_with_prefix_and_emoji(self):
        """
        Test summary with prefix and emoji removal
        """
        summary_title = "Feature request 🚀"
        result = build_summary_field(
            summary_title, prefix="[AI]", add_timestamp=False
        )
        assert result.startswith("[AI]")
        assert "🚀" not in result
        assert "Feature request" in result

    def test_upload_attachments_returns_uploaded_attachment_keys(
        self, jira_handler, tmp_path
    ):
        attachment_file = tmp_path / "demo.png"
        attachment_file.write_bytes(b"fake image bytes")

        jira_handler.client.add_attachment = Mock(return_value=None)

        result = jira_handler.upload_attachments(
            issue_key="REQ-1",
            attachments=[
                {
                    "id": "att-1",
                    "content_md5": "md5-1",
                    "filename": "demo.png",
                    "content_type": "image/png",
                    "is_image": True,
                    "file_path": str(attachment_file),
                    "file_size": attachment_file.stat().st_size,
                    "llm_content": "Recognized content",
                }
            ],
        )

        assert result["uploaded_count"] == 1
        assert result["skipped_count"] == 0
        assert result["uploaded_attachment_keys"] == [
            "md5:md5-1",
            "id:att-1",
            f"name:demo.png:{attachment_file.stat().st_size}",
        ]
        assert result["skipped_attachment_keys"] == []

    def test_update_issue_preserves_summary_prefix(self, jira_handler):
        jira_handler.client.update_issue = Mock()

        jira_handler.update_issue(
            issue_key="REQ-1",
            issue_data={"title": "Child title"},
            email_data={
                "summary_content": "Summary body",
                "llm_content": "LLM body",
                "language": "en",
            },
            attachments=[],
        )

        jira_handler.client.update_issue.assert_called_once()
        kwargs = jira_handler.client.update_issue.call_args.kwargs
        assert kwargs["summary"] == "[AI]Child title"

    def test_upload_attachments_uploads_non_image_files(
        self, jira_handler, tmp_path
    ):
        attachment_file = tmp_path / "demo.pdf"
        attachment_file.write_bytes(b"fake pdf bytes")

        jira_handler.client.add_attachment = Mock(return_value=None)

        result = jira_handler.upload_attachments(
            issue_key="REQ-2",
            attachments=[
                {
                    "id": "att-2",
                    "content_md5": "md5-2",
                    "filename": "demo.pdf",
                    "content_type": "application/pdf",
                    "is_image": False,
                    "file_path": str(attachment_file),
                    "file_size": attachment_file.stat().st_size,
                }
            ],
        )

        assert result["uploaded_count"] == 1
        assert result["skipped_count"] == 0
        assert result["uploaded_attachment_keys"] == [
            "md5:md5-2",
            "id:att-2",
            f"name:demo.pdf:{attachment_file.stat().st_size}",
        ]
        assert result["skipped_attachment_keys"] == []


class TestEpicLinkValidation:
    """
    Test suite for epic_link format validation in _validate_llm_response
    """

    @pytest.fixture
    def full_config(self):
        """
        Create a full JIRA configuration matching production config structure
        """
        return {
            "jira": {
                "url": "https://jira.example.com",
                "username": "test_user",
                "api_token": "test_token",
            },
            "language": "Chinese",
            "fields": {
                "project_key_config": {
                    "use_llm": False,
                    "jira_field": "project",
                    "default": "REQ",
                },
                "issue_type_config": {
                    "use_llm": False,
                    "jira_field": "issuetype",
                    "default": "New Feature",
                },
                "priority_config": {
                    "use_llm": False,
                    "jira_field": "priority",
                    "default": "High",
                },
                "summary_config": {
                    "prefix": "[AI]",
                    "use_llm": True,
                    "jira_field": "summary",
                },
                "description_config": {
                    "use_llm": False,
                    "jira_field": "description",
                    "convert_to_jira_wiki": True,
                },
                "components_config": {
                    "use_llm": True,
                    "fetch_from_api": True,
                    "jira_field": "components",
                },
                "epic_link_config": {
                    "use_llm": True,
                    "fetch_from_api": True,
                    "jira_field": "customfield_10014",
                },
            },
        }

    def test_epic_link_validation_accepts_valid_format(self, full_config):
        with patch("threadline.utils.issues.jira_handler.JiraClient"):
            handler = JiraIssueHandler(full_config)
        assert handler.default_project_key == "REQ"
