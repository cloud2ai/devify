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

    sentry_sdk.init(
        dsn=_DSN,
        environment=os.getenv("SENTRY_ENVIRONMENT", "production"),
        release=os.getenv("SENTRY_RELEASE", ""),
        # Capture a fraction of transactions for performance monitoring.
        # Set to 0.0 to disable tracing without removing the integration.
        traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1")),
        # Profiling runs inside sampled transactions only.
        profiles_sample_rate=float(os.getenv("SENTRY_PROFILES_SAMPLE_RATE", "0.0")),
        send_default_pii=os.getenv("SENTRY_SEND_PII", "false").lower() == "true",
        integrations=[
            DjangoIntegration(),
            CeleryIntegration(),
            RedisIntegration(),
            LoggingIntegration(),
        ],
    )
