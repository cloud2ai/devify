"""
Unit tests for JiraIssueHandler emoji removal functionality.
"""

import pytest
from unittest.mock import Mock, patch

from threadline.utils.issues.jira_handler import JiraIssueHandler


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
            'url': 'https://jira.example.com',
            'username': 'test_user',
            'api_token': 'test_token',
            'project_key': 'TEST',
            'default_issue_type': 'Task',
            'default_priority': 'Medium',
            'summary_prefix': '[AI]',
            'summary_timestamp': False,
        }

    @pytest.fixture
    def jira_handler(self, jira_config):
        """
        Create a JiraIssueHandler instance for testing
        """
        with patch(
            'threadline.utils.issues.jira_handler.JiraClient'
        ):
            handler = JiraIssueHandler(jira_config)
            return handler

    def test_remove_emoji_removes_emoticons(self, jira_handler):
        """
        Test that emoticons are removed from text
        """
        text_with_emoji = "Hello 😀 World 😃 Test 😄"
        result = jira_handler._remove_emoji(text_with_emoji)
        assert result == "Hello  World  Test "

    def test_remove_emoji_removes_symbols(self, jira_handler):
        """
        Test that symbol emojis are removed from text
        """
        text_with_emoji = "Weather: ☀️ ⛅ ☁️ ⚡"
        result = jira_handler._remove_emoji(text_with_emoji)
        assert "☀" not in result
        assert "⛅" not in result

    def test_remove_emoji_handles_empty_string(self, jira_handler):
        """
        Test that empty string is handled correctly
        """
        result = jira_handler._remove_emoji("")
        assert result == ""

    def test_remove_emoji_handles_none(self, jira_handler):
        """
        Test that None is handled correctly
        """
        result = jira_handler._remove_emoji(None)
        assert result == ""

    def test_remove_emoji_preserves_normal_text(self, jira_handler):
        """
        Test that normal text without emoji is preserved
        """
        text = "This is a normal text without any emoji"
        result = jira_handler._remove_emoji(text)
        assert result == text

    def test_clean_jira_summary_removes_emoji(self, jira_handler):
        """
        Test that clean_jira_summary removes emoji from summary
        """
        summary_with_emoji = "Fix bug 🐛 in login 🔐 system"
        result = jira_handler._clean_jira_summary(summary_with_emoji)
        assert "🐛" not in result
        assert "🔐" not in result
        assert "Fix bug" in result
        assert "in login" in result

    def test_clean_jira_summary_removes_newlines(self, jira_handler):
        """
        Test that clean_jira_summary removes newlines
        """
        summary_with_newlines = "First line\nSecond line\r\nThird line"
        result = jira_handler._clean_jira_summary(summary_with_newlines)
        assert "\n" not in result
        assert "\r" not in result
        # Note: \r\n becomes two spaces (one for \r, one for \n)
        assert "First line Second line  Third line" == result

    def test_clean_jira_summary_removes_emoji_and_newlines(
        self, jira_handler
    ):
        """
        Test that clean_jira_summary removes both emoji and newlines
        """
        summary = "Bug 🐛 report\nLogin issue 🔐"
        result = jira_handler._clean_jira_summary(summary)
        assert "🐛" not in result
        assert "🔐" not in result
        assert "\n" not in result
        assert "Bug  report Login issue " == result

    def test_clean_jira_summary_handles_empty_string(self, jira_handler):
        """
        Test that clean_jira_summary handles empty string
        """
        result = jira_handler._clean_jira_summary("")
        assert result == ""

    def test_build_jira_summary_removes_emoji(self, jira_handler):
        """
        Test that build_jira_summary removes emoji from final summary
        """
        email_data = {
            'summary_title': 'Bug 🐛 in payment 💳 system',
            'subject': 'Bug report',
            'id': 'test-email-123'
        }
        result = jira_handler._build_jira_summary(email_data)
        assert "🐛" not in result
        assert "💳" not in result
        assert "[AI]Bug  in payment  system" == result

    def test_build_jira_summary_with_prefix_and_emoji(self, jira_handler):
        """
        Test summary with prefix and emoji removal
        """
        email_data = {
            'summary_title': 'Feature request 🚀',
            'subject': 'New feature',
            'id': 'test-email-456'
        }
        result = jira_handler._build_jira_summary(email_data)
        assert result.startswith('[AI]')
        assert "🚀" not in result
        assert "Feature request" in result
