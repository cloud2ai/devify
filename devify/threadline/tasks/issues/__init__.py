"""
Issues package for external system integrations.

This package contains implementations for different issue tracking systems:
- JIRA integration
- Future: GitHub Issues, GitLab Issues, etc.
"""

from .jira_handler import JiraIssueHandler

__all__ = ['JiraIssueHandler']
