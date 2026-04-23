"""Logging configuration for the Django application.

This module disables Django's default logging setup and installs a custom
configuration with a console handler, application loggers, and a few noisy
third-party logger overrides.
"""

import logging
import logging.config
import os

from celery import current_task
from django.utils.log import DEFAULT_LOGGING

# Disable Django's logging setup
LOGGING_CONFIG = None

_ORIGINAL_LOG_RECORD_FACTORY = logging.getLogRecordFactory()
WORKER_LOG_FILE = os.getenv("THREADLINE_LOG_FILE")


def _current_task_id() -> str:
    try:
        request = getattr(current_task, "request", None)
        task_id = getattr(request, "id", None)
        if task_id:
            return str(task_id)
    except Exception:
        pass
    return "-"


class TaskIdFormatter(logging.Formatter):
    def format(self, record):
        if not hasattr(record, "task_id"):
            record.task_id = _current_task_id()
        return super().format(record)


def _task_id_log_record_factory(*args, **kwargs):
    record = _ORIGINAL_LOG_RECORD_FACTORY(*args, **kwargs)
    if not hasattr(record, "task_id"):
        record.task_id = _current_task_id()
    return record


def configure_logging(log_level="INFO"):
    """
    Configures the logging settings for the application.

    Args:
        log_level (str): The logging level to set. Defaults to "INFO".
    """
    logging.setLogRecordFactory(_task_id_log_record_factory)
    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "()": TaskIdFormatter,
                "format": (
                    "[%(asctime)s][%(levelname)s]"
                    "[task_id=%(task_id)s] %(message)s"
                ),
            },
            "django.server": DEFAULT_LOGGING["formatters"]["django.server"],
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "default",
            },
            "django.server": DEFAULT_LOGGING["handlers"]["django.server"],
        },
        "loggers": {
            "": {
                "level": log_level,
                "handlers": ["console"],
            },
            "core": {
                "level": log_level,
                "handlers": ["console"],
                "propagate": False,
            },
            "django.server": DEFAULT_LOGGING["loggers"]["django.server"],
            "django.utils.autoreload": {
                "level": "INFO",
                "handlers": ["console"],
                "propagate": False,
            },
            # Third-party libraries that get noisy during startup or
            # network calls. Keep them at WARNING for readability.
            "litellm": {
                "level": "WARNING",
                "handlers": ["console"],
                "propagate": False,
            },
            "LiteLLM": {
                "level": "WARNING",
                "handlers": ["console"],
                "propagate": False,
            },
            "httpcore": {
                "level": "WARNING",
                "handlers": ["console"],
                "propagate": False,
            },
            "httpx": {
                "level": "WARNING",
                "handlers": ["console"],
                "propagate": False,
            },
            "aiohttp": {
                "level": "WARNING",
                "handlers": ["console"],
                "propagate": False,
            },
            "asyncio": {
                "level": "WARNING",
                "handlers": ["console"],
                "propagate": False,
            },
            # Suppress Celery system DEBUG logs
            "celery": {
                "level": "WARNING",
                "handlers": ["console"],
                "propagate": False,
            },
            "celery.utils.functional": {
                "level": "WARNING",
                "handlers": ["console"],
                "propagate": False,
            },
            "celery.worker": {
                "level": "WARNING",
                "handlers": ["console"],
                "propagate": False,
            },
            "celery.app": {
                "level": "WARNING",
                "handlers": ["console"],
                "propagate": False,
            },
            # Suppress flanker warnings
            "flanker": {
                "level": "ERROR",
                "handlers": ["console"],
                "propagate": False,
            },
            "flanker.addresslib._parser.parser": {
                "level": "ERROR",
                "handlers": ["console"],
                "propagate": False,
            },
        },
    }

    if WORKER_LOG_FILE:
        os.makedirs(os.path.dirname(WORKER_LOG_FILE), exist_ok=True)
        config["handlers"]["worker_file"] = {
            "class": "logging.FileHandler",
            "filename": WORKER_LOG_FILE,
            "formatter": "default",
        }
        worker_logger_names = [
            "",
            "core",
            "django.utils.autoreload",
            "litellm",
            "LiteLLM",
            "httpcore",
            "httpx",
            "aiohttp",
            "asyncio",
            "celery",
            "celery.utils.functional",
            "celery.worker",
            "celery.app",
            "flanker",
            "flanker.addresslib._parser.parser",
        ]
        for logger_name in worker_logger_names:
            config["loggers"][logger_name] = {
                "level": log_level
                if logger_name in ("", "core")
                else "WARNING",
                "handlers": ["worker_file"],
                "propagate": False,
            }

    logging.config.dictConfig(config)
