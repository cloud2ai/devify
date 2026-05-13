"""
Issue handler factory.

This module provides a small factory for selecting the configured issue
provider handler.
"""

from typing import Any, Dict


def normalize_issue_engine(issue_engine: str | None) -> str:
    """
    Normalize an issue engine name to its canonical identifier.

    Kept intentionally small so config files can use canonical engine names
    while normalization still removes incidental whitespace or casing.
    """
    normalized = str(issue_engine or "jira").strip().lower()
    return normalized


def get_issue_handler(config: Dict[str, Any]):
    """
    Create an issue handler for the configured engine.

    Args:
        config: Issue configuration dictionary from settings

    Returns:
        A concrete issue handler instance

    Raises:
        ValueError: If the configured engine is unsupported
    """
    issue_engine = normalize_issue_engine(config.get("issue_engine", "jira"))

    if issue_engine == "jira":
        from relay.services.drivers.jira_handler import JiraIssueHandler

        handler_class = JiraIssueHandler
    elif issue_engine == "feishu_bitable":
        from relay.services.drivers.feishu_bitable_handler import (
            FeishuBitableIssueHandler,
        )

        handler_class = FeishuBitableIssueHandler
    else:
        handler_class = None

    if not handler_class:
        raise ValueError(f"Unsupported issue engine: {issue_engine}")

    return handler_class(config)
