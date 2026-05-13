"""
Reusable fake issue handlers for integration tests.
"""

from unittest.mock import Mock


def build_issue_handler(issue_key: str = "REQ-123", issue_url: str | None = None):
    """
    Create a predictable fake issue handler.
    """

    handler = Mock()
    handler.issue_key = issue_key
    handler.issue_url = issue_url or f"https://jira.example.com/browse/{issue_key}"
    handler.create_issue.return_value = issue_key
    handler.update_issue.return_value = issue_key
    handler.get_issue_url.return_value = handler.issue_url
    handler.link_issue.return_value = True
    handler.link_related_issues.return_value = {
        "linked_count": 1,
        "skipped_count": 0,
    }
    return handler
