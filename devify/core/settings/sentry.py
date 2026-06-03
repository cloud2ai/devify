"""
Sentry SDK configuration.

Sentry is opt-in: the SDK is only initialised when SENTRY_DSN is set.
Leaving SENTRY_DSN unset (or empty) in an environment disables all
monitoring without any code changes.
"""

import os

_DSN = os.getenv("SENTRY_DSN", "").strip()

if _DSN:
    import sentry_sdk
    from sentry_sdk.integrations.celery import CeleryIntegration
    from sentry_sdk.integrations.django import DjangoIntegration
    from sentry_sdk.integrations.logging import LoggingIntegration
    from sentry_sdk.integrations.redis import RedisIntegration

    # MySQL error codes that indicate the server is unreachable at connect
    # time. These only occur during startup or restart and are handled by
    # the caller.
    _MYSQL_STARTUP_ERROR_CODES = {
        2003,  # Can't connect to MySQL server (connection refused)
        2005,  # Unknown MySQL server host (DNS failure)
    }

    # Log message prefixes emitted by Celery internals when the broker is
    # temporarily unreachable during startup. These are not actionable.
    _CELERY_BROKER_TRANSIENT_PREFIXES = (
        "consumer: Cannot connect to redis://",
        "consumer: Cannot connect to amqp://",
    )

    def _before_send(event, hint):
        """
        Drop transient infrastructure-connectivity errors that are expected
        during container restarts and are already handled in application code.
        """
        # Drop Celery consumer broker-unreachable log messages. These are
        # emitted by Celery itself (not our code) when the broker is briefly
        # unavailable on startup; Celery reconnects automatically.
        message = (
            event.get("logentry", {}).get("message", "")
            or event.get("message", "")
            or ""
        )
        if message.startswith(_CELERY_BROKER_TRANSIENT_PREFIXES):
            return None

        exc_info = hint.get("exc_info")
        if exc_info:
            exc_type, exc_value, _ = exc_info
            # Drop Celery Beat SchedulingError: Redis temporarily unreachable
            # during restart; the scheduler retries on the next beat tick.
            if exc_type.__name__ == "SchedulingError":
                return None
            # Drop MySQL connection-refused / DNS-failure errors that only
            # occur when the database container is still starting up.
            if exc_type.__name__ == "OperationalError":
                raw_args = getattr(exc_value, "args", ())
                code = (
                    raw_args[0]
                    if raw_args and isinstance(raw_args[0], int)
                    else None
                )
                if code in _MYSQL_STARTUP_ERROR_CODES:
                    return None
        return event

    sentry_sdk.init(
        dsn=_DSN,
        environment=os.getenv("SENTRY_ENVIRONMENT", "production"),
        release=os.getenv("SENTRY_RELEASE", ""),
        # Capture a fraction of transactions for performance monitoring.
        # Set to 0.0 to disable tracing without removing the integration.
        traces_sample_rate=float(
            os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1")
        ),
        # Profiling runs inside sampled transactions only.
        profiles_sample_rate=float(
            os.getenv("SENTRY_PROFILES_SAMPLE_RATE", "0.0")
        ),
        send_default_pii=(
            os.getenv("SENTRY_SEND_PII", "false").lower() == "true"
        ),
        before_send=_before_send,
        integrations=[
            DjangoIntegration(),
            CeleryIntegration(),
            RedisIntegration(),
            LoggingIntegration(),
        ],
    )
