"""
Issue management utilities.

This package provides utilities for integrating with external issue
tracking systems like JIRA and Feishu Bitable.
"""

from .feishu_bitable_handler import FeishuBitableIssueHandler
from .issue_factory import get_issue_handler
from .jira_handler import JiraIssueHandler

__all__ = [
    'FeishuBitableIssueHandler',
    'JiraIssueHandler',
    'get_issue_handler',
]
