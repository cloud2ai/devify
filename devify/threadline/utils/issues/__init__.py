"""
Issue management utilities.

This package provides utilities for integrating with external issue
tracking systems like JIRA, GitHub, Slack, etc.
"""

from .jira_handler import JiraIssueHandler

__all__ = ['JiraIssueHandler']
