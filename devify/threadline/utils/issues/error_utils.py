"""Issue error helpers."""

from __future__ import annotations


def is_missing_issue_error(exc: Exception) -> bool:
    """Return True when an external issue no longer exists."""
    message = str(exc).lower()
    return any(
        token in message
        for token in (
            "issue does not exist",
            "issue not found",
            "does not exist",
            "not found",
            "问题不存在",
            "404",
        )
    )
