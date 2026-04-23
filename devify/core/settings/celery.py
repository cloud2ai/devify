import os

# For production environments, use Redis or RabbitMQ as result backend.
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379")

# Use Django database as result backend.
CELERY_RESULT_BACKEND = "django-db"

# Keep Django logging active in worker processes so the application formatter
# can remain in control.
CELERY_WORKER_HIJACK_ROOT_LOGGER = False

# Match the application log format and include the Celery task id when
# worker-side task log records are emitted.
CELERY_WORKER_LOG_FORMAT = (
    "[%(asctime)s][%(levelname)s][task_id=%(task_id)s] %(message)s"
)
CELERY_WORKER_TASK_LOG_FORMAT = (
    "[%(asctime)s][%(levelname)s][task_id=%(task_id)s] %(message)s"
)

# Set the default scheduler for Celery Beat
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"

# The CELERY_ACCEPT_CONTENT setting determines the message content types that
# Celery can accept. Setting it to ['json'] means that Celery only accepts JSON
# formatted message content. By default, Celery supports multiple content types
# (such as pickle, json, yaml, msgpack). Using JSON is for security and
# compatibility reasons. JSON format is lightweight, cross-platform, and less
# likely to cause potential security issues (such as pickle deserialization
# vulnerabilities).
CELERY_ACCEPT_CONTENT = ["json"]

# The CELERY_TASK_SERIALIZER setting specifies how Celery serializes the task
# message content. Setting it to 'json' means that Celery will serialize the
# task content into JSON format. The purpose of this is to ensure that the task
# content can be transmitted and stored across platforms. JSON is a universal,
# lightweight serialization format that can transfer data between different
# languages and systems. Other optional serialization formats include pickle
# (not recommended, may have security risks), msgpack (more efficient
# compression), and yaml (more readable but less efficient).
CELERY_TASK_SERIALIZER = "json"

# Prevent task loss in Redis
CELERY_BROKER_TRANSPORT_OPTIONS = {
    "visibility_timeout": 43200,
    "fanout_prefix": True,
    "fanout_patterns": True,
}

# Task execution time limits
CELERY_TASK_TIME_LIMIT = 3600
CELERY_TASK_SOFT_TIME_LIMIT = 3000

# Task result expiration (keep results for 7 days)
CELERY_RESULT_EXPIRES = 604800

# Task acknowledgment settings
CELERY_TASK_ACKS_LATE = True

# Prefetch multiplier (configurable based on worker setup)
CELERY_WORKER_PREFETCH_MULTIPLIER = int(
    os.getenv("CELERY_WORKER_PREFETCH_MULTIPLIER", 4)
)

# Periodic tasks are registered at runtime via:
#   python manage.py register_periodic_tasks
CELERY_BEAT_SCHEDULE = {}
