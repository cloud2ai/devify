"""
Unit tests for JiraIssueHandler emoji removal functionality.
"""

import pytest
from unittest.mock import Mock, patch

from threadline.utils.issues.jira_handler import JiraIssueHandler
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
