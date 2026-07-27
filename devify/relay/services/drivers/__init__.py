"""Canonical Relay driver entrypoints.

Relay owns the delivery drivers now. Threadline keeps compatibility imports
only so legacy code paths do not break immediately.
"""

from .github_issue_handler import GitHubIssueHandler
from .jira_handler import JiraIssueHandler

__all__ = [
    "FeishuBitableIssueHandler",
    "GitHubIssueHandler",
    "JiraIssueHandler",
]


def __getattr__(name):
    if name == "FeishuBitableIssueHandler":
        # Deferred: lark_oapi (~3.4 s) only needed when Feishu delivery runs.
        from .feishu_bitable_handler import FeishuBitableIssueHandler
        return FeishuBitableIssueHandler
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
