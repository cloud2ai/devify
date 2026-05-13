"""
Issue merge and retry policy helpers for the email processing workflow.
"""

_RETRY_TRIGGER_SOURCES = {"retry_task", "api_retry"}

_DEFAULT_POLICY = {
    "auto_merge_strategy": "new",
    "retry_issue_strategy": "update",
}


def get_issue_merge_policy(issue_config: dict) -> dict:
    """Return the merge/retry strategy from issue_config, falling back to defaults."""
    if not isinstance(issue_config, dict):
        return dict(_DEFAULT_POLICY)
    return {
        "auto_merge_strategy": issue_config.get(
            "auto_merge_strategy", _DEFAULT_POLICY["auto_merge_strategy"]
        ),
        "retry_issue_strategy": issue_config.get(
            "retry_issue_strategy", _DEFAULT_POLICY["retry_issue_strategy"]
        ),
    }


def is_retry_trigger_source(trigger_source: str | None) -> bool:
    """Return True when the workflow was triggered by a manual or automatic retry."""
    return trigger_source in _RETRY_TRIGGER_SOURCES
