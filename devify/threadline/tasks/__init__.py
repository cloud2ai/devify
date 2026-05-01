"""Task package exports for threadline.

Keep package import side effects minimal so Django/Celery startup does not
pull the whole task graph in eagerly. The actual task modules are imported
explicitly in `ThreadlineConfig.ready()` for registration, while this module
provides lazy attribute access for legacy imports.
"""

from __future__ import annotations

from importlib import import_module

__all__ = [
    "process_email_workflow",
    "retry_failed_email_workflow",
    "process_email_merge",
    "schedule_email_fetch",
    "scan_user_emails",
    "send_threadline_failure_notification",
    "send_threadline_notification",
]

_EXPORTS = {
    "process_email_workflow": (
        "threadline.tasks.email_workflow",
        "process_email_workflow",
    ),
    "retry_failed_email_workflow": (
        "threadline.tasks.email_workflow",
        "retry_failed_email_workflow",
    ),
    "process_email_merge": (
        "threadline.tasks.email_merge",
        "process_email_merge",
    ),
    "schedule_email_fetch": (
        "threadline.tasks.scheduler",
        "schedule_email_fetch",
    ),
    "scan_user_emails": (
        "threadline.tasks.email_fetch",
        "fetch_user_imap_emails",
    ),
    "send_threadline_failure_notification": (
        "threadline.tasks.notifications",
        "send_threadline_failure_notification",
    ),
    "send_threadline_notification": (
        "threadline.tasks.notifications",
        "send_threadline_notification",
    ),
}


def __getattr__(name: str):
    if name not in _EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module_path, attr_name = _EXPORTS[name]
    module = import_module(module_path)
    value = getattr(module, attr_name)
    globals()[name] = value
    return value
