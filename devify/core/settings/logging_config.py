"""
Logging Configuration

This module customizes the logging settings for the Django application.
By disabling Django's default logging setup and defining a custom configuration,
it ensures consistent and structured logging output.

- `LOGGING_CONFIG`: Disabled to prevent Django from applying default settings.
- `configure_logging`: Function to set up logging with the specified log level.
  It defines formatters, handlers, and loggers for various application components.

Highlights:
- Logs are formatted to include timestamps, logger names, log levels, and messages.
- A `console` handler is configured to output logs to stderr.
- The `core` logger is customized to avoid propagating logs to the root logger.
- Suppresses DEBUG logs for `django.utils.autoreload` by setting its level to INFO.
"""

import logging.config
import os

from django.utils.log import DEFAULT_LOGGING

# Disable Django's logging setup
LOGGING_CONFIG = None

def configure_logging(log_level="INFO"):
    """
    Configures the logging settings for the application.

    Args:
        log_level (str): The logging level to set. Defaults to "INFO".
    """
    logging.config.dictConfig({
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'default': {
                'format': '%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
            },
            'django.server': DEFAULT_LOGGING['formatters']['django.server'],
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'formatter': 'default',
            },
            'django.server': DEFAULT_LOGGING['handlers']['django.server'],
        },
        'loggers': {
            '': {
                'level': log_level,
                'handlers': ['console'],
            },
            'core': {
                'level': log_level,
                'handlers': ['console'],
                'propagate': False,
            },
            'django.server': DEFAULT_LOGGING['loggers']['django.server'],
            'django.utils.autoreload': {
                'level': 'INFO',
                'handlers': ['console'],
                'propagate': False,
            },
        },
    })
