"""
Issue management utilities.

This package provides utilities for integrating with external issue
tracking systems like JIRA and Feishu Bitable.
"""

from .issue_factory import get_issue_handler

__all__ = [
    "get_issue_handler",
]
