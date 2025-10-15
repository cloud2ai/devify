import os

from celery.schedules import crontab

# For production environments, use Redis or RabbitMQ as result backend.
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL",
                               "redis://localhost:6379")

# Use Django database as result backend.
CELERY_RESULT_BACKEND = 'django-db'

# Set the default scheduler for Celery Beat
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'

# The CELERY_ACCEPT_CONTENT setting determines the message content types that
# Celery can accept. Setting it to ['json'] means that Celery only accepts JSON
# formatted message content. By default, Celery supports multiple content types
# (such as pickle, json, yaml, msgpack). Using JSON is for security and
# compatibility reasons. JSON format is lightweight, cross-platform, and less
# likely to cause potential security issues (such as pickle deserialization
# vulnerabilities).
CELERY_ACCEPT_CONTENT = ['json']

# The CELERY_TASK_SERIALIZER setting specifies how Celery serializes the task
# message content. Setting it to 'json' means that Celery will serialize the
# task content into JSON format. The purpose of this is to ensure that the task
# content can be transmitted and stored across platforms. JSON is a universal,
# lightweight serialization format that can transfer data between different
# languages and systems. Other optional serialization formats include pickle
# (not recommended, may have security risks), msgpack (more efficient
# compression), and yaml (more readable but less efficient).
CELERY_TASK_SERIALIZER = 'json'

# Prevent task loss in Redis
CELERY_BROKER_TRANSPORT_OPTIONS = {
    'visibility_timeout': 43200,
    'fanout_prefix': True,
    'fanout_patterns': True,
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
    os.getenv('CELERY_WORKER_PREFETCH_MULTIPLIER', 4)
)

# Celery periodic task scheduling configuration, defining tasks that need to
# run periodically
CELERY_BEAT_SCHEDULE = {
    # Unified email fetching scheduler - runs every minute
    'schedule_email_fetch': {
        'task': 'threadline.tasks.scheduler.schedule_email_fetch',
        'schedule': crontab(minute='*/1'),
        'args': (),
        'kwargs': {},
    },
    # Reset stuck emails (FETCHED and PROCESSING) - runs every 30 minutes
    'reset_stuck_emails': {
        'task': 'threadline.tasks.scheduler.schedule_reset_stuck_emails',
        'schedule': crontab(minute='*/30'),
        'args': (),
        'kwargs': {'timeout_minutes': 30},
    },

    # Haraka email files cleanup - runs daily at 2 AM
    'schedule_haraka_cleanup': {
        'task': 'threadline.tasks.scheduler.schedule_haraka_cleanup',
        'schedule': crontab(hour=2, minute=0),
        'args': (),
        'kwargs': {},
    },

    # EmailTask records cleanup - runs daily at 3 AM
    'schedule_email_task_cleanup': {
        'task': 'threadline.tasks.scheduler.schedule_email_task_cleanup',
        'schedule': crontab(hour=3, minute=0),
        'args': (),
        'kwargs': {},
    },
}
