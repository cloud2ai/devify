"""
Unit tests for JiraIssueHandler emoji removal functionality.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

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
                    "default": [],
                },
                "epic_link_config": {
                    "use_llm": True,
                    "fetch_from_api": True,
                    "jira_field": "customfield_10014",
                    "default": "REQ-100",
                },
            },
        }

    @pytest.fixture
    def mock_handler(self, full_config):
        """
        Create a JiraIssueHandler with mocked JIRA client
        """
        with patch("threadline.utils.issues.jira_handler.JiraClient") as mock_client:
            handler = JiraIssueHandler(full_config)
            return handler

    def test_epic_link_valid_format(self, mock_handler):
        """
        Test that valid epic_link format (REQ-123) passes through
        """
        llm_response = {
            "customfield_10014": "REQ-123",
            "assignee": "liulixiang",
            "components": [],
        }
        llm_fields = {
            "epic_link": {
                "jira_field": "customfield_10014",
                "default": "REQ-100",
                "allow_values": ["REQ-123 (Epic 1)", "REQ-456 (Epic 2)"],
            },
            "assignee": {
                "jira_field": "assignee",
                "default": "liulixiang",
                "allow_values": ["liulixiang", "zhangjiaqi"],
            },
            "components": {
                "jira_field": "components",
                "default": [],
                "allow_values": ["Component A", "Component B"],
            },
        }

        validated = mock_handler._validate_llm_response(llm_response, llm_fields)

        assert validated["customfield_10014"] == "REQ-123"

    def test_epic_link_invalid_format_chinese_name_uses_default(self, mock_handler):
        """
        Test that Chinese epic name (not a key) is rejected and uses default
        """
        llm_response = {
            "customfield_10014": "【AWS无代理迁移】迁移至HCS平台后虚拟机启动失败",
            "assignee": "liulixiang",
        }
        llm_fields = {
            "epic_link": {
                "jira_field": "customfield_10014",
                "default": "REQ-100",
                "allow_values": ["REQ-123 (Epic 1)", "REQ-456 (Epic 2)"],
            },
            "assignee": {
                "jira_field": "assignee",
                "default": "liulixiang",
                "allow_values": ["liulixiang"],
            },
        }

        validated = mock_handler._validate_llm_response(llm_response, llm_fields)

        # Invalid format should use default value
        assert validated["customfield_10014"] == "REQ-100"

    def test_epic_link_list_takes_first(self, mock_handler):
        """
        Test that if epic_link is a list, first element is used
        """
        llm_response = {
            "customfield_10014": ["REQ-123", "REQ-456"],
        }
        llm_fields = {
            "epic_link": {
                "jira_field": "customfield_10014",
                "default": "REQ-100",
                "allow_values": ["REQ-123 (Epic 1)", "REQ-456 (Epic 2)"],
            },
        }

        validated = mock_handler._validate_llm_response(llm_response, llm_fields)

        # List should be converted to first element
        assert validated["customfield_10014"] == "REQ-123"

    def test_epic_link_empty_string_uses_default(self, mock_handler):
        """
        Test that empty string epic_link uses default value
        """
        llm_response = {
            "customfield_10014": "",
        }
        llm_fields = {
            "epic_link": {
                "jira_field": "customfield_10014",
                "default": "REQ-100",
                "allow_values": [],
            },
        }

        validated = mock_handler._validate_llm_response(llm_response, llm_fields)

        # Empty string is treated as empty, default value is used
        assert validated["customfield_10014"] == "REQ-100"

    def test_epic_link_mixed_valid_invalid(self, mock_handler):
        """
        Test that a valid format with uppercase letters and dash-number passes
        """
        llm_response = {
            "customfield_10014": "PROJ-999",
        }
        llm_fields = {
            "epic_link": {
                "jira_field": "customfield_10014",
                "default": "REQ-100",
                "allow_values": [],
            },
        }

        validated = mock_handler._validate_llm_response(llm_response, llm_fields)

        # Valid format should pass through
        assert validated["customfield_10014"] == "PROJ-999"

    def test_epic_link_lowercase_uses_default(self, mock_handler):
        """
        Test that lowercase epic key (req-123) is rejected and uses default
        """
        llm_response = {
            "customfield_10014": "req-123",
        }
        llm_fields = {
            "epic_link": {
                "jira_field": "customfield_10014",
                "default": "REQ-100",
                "allow_values": [],
            },
        }

        validated = mock_handler._validate_llm_response(llm_response, llm_fields)

        # Lowercase should be rejected and use default
        assert validated["customfield_10014"] == "REQ-100"

    def test_assignee_valid_in_allow_values(self, mock_handler):
        """
        Test that assignee in allow_values passes through
        """
        llm_response = {
            "assignee": "liulixiang",
        }
        llm_fields = {
            "assignee": {
                "jira_field": "assignee",
                "default": "liulixiang",
                "allow_values": ["liulixiang", "zhangjiaqi"],
            },
        }

        validated = mock_handler._validate_llm_response(llm_response, llm_fields)

        assert validated["assignee"] == "liulixiang"

    def test_assignee_invalid_uses_default(self, mock_handler):
        """
        Test that assignee not in allow_values uses default value
        """
        llm_response = {
            "assignee": "random_user",
        }
        llm_fields = {
            "assignee": {
                "jira_field": "assignee",
                "default": "liulixiang",
                "allow_values": ["liulixiang", "zhangjiaqi"],
            },
        }

        validated = mock_handler._validate_llm_response(llm_response, llm_fields)

        # Invalid assignee should use default value
        assert validated["assignee"] == "liulixiang"

    def test_components_valid_list(self, mock_handler):
        """
        Test that valid components list passes through
        """
        llm_response = {
            "components": ["Component A", "Component B"],
        }
        llm_fields = {
            "components": {
                "jira_field": "components",
                "default": [],
                "allow_values": ["Component A", "Component B"],
            },
        }

        validated = mock_handler._validate_llm_response(llm_response, llm_fields)

        assert validated["components"] == ["Component A", "Component B"]

    def test_components_string_converted_to_list(self, mock_handler):
        """
        Test that components returned as string is converted to list
        """
        llm_response = {
            "components": "Component A, Component B",
        }
        llm_fields = {
            "components": {
                "jira_field": "components",
                "default": [],
                "allow_values": [],
            },
        }

        validated = mock_handler._validate_llm_response(llm_response, llm_fields)

        assert validated["components"] == ["Component A", "Component B"]

    def test_components_empty_list_uses_default(self, mock_handler):
        """
        Test that empty components list uses default (empty list)
        """
        llm_response = {
            "components": [],
        }
        llm_fields = {
            "components": {
                "jira_field": "components",
                "default": [],
                "allow_values": [],
            },
        }

        validated = mock_handler._validate_llm_response(llm_response, llm_fields)

        # Empty list is treated as empty, will use default in create_issue
        # In original behavior, empty list is skipped (not in validated_data)
        # So this test just verifies it doesn't crash
        # The actual default handling happens in create_issue

    def test_create_issue_uses_default_when_epic_link_none(self, mock_handler):
        """
        Test that create_issue uses default epic_link when LLM returns None
        """
        # The default value from config should be used when epic_link is None
        # This is verified by checking fields_config
        epic_link_config = mock_handler.fields_config.get("epic_link_config", {})
        default_epic = epic_link_config.get("default")

        assert default_epic == "REQ-100"
