import os

from celery.schedules import crontab

# For production environments, use Redis or RabbitMQ as result backend.
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL",
                               "redis://localhost:6379")
# Use Redis as result backend, or Django database.
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND",
                                   "redis://localhost:6379")

# Set the default scheduler for Celery Beat
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'

# Use Django database as result backend.
CELERY_RESULT_BACKEND = 'django-db'


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

# Celery periodic task scheduling configuration, defining tasks that need to
# run periodically
CELERY_BEAT_SCHEDULE = {
    # The unique identifier name of the periodic task, can be defined arbitrarily
    # but must be globally unique
    'sample_heartbeat': {
        # Specify the path of the Celery task, must be a task defined in the project
        # For example, the heartbeat function defined in cloud_platform/tasks.py
        # 'task': 'v1.sample.tasks.heartbeat',

        # Define the task schedule
        # 1. Use crontab expression to simulate cron periodic tasks
        #    For example: minute="*/1" means the task is executed every minute
        # 2. Other common options:
        #    - crontab(minute=0, hour=0): executed once every midnight at 0:00
        #    - crontab(day_of_week="1", hour=10, minute=0): executed once every
        #      Monday at 10:00 AM
        #    - crontab(hour="*/3", minute=0): executed once every 3 hours
        # 3. Besides crontab, you can also define the schedule using the following
        #    methods:
        #    - `timedelta(seconds=300)`: executed every 5 minutes (based on fixed
        #      intervals)
        #    - Custom time scheduler (need to inherit and implement
        #      celery.schedules.schedule)
        # 'schedule': crontab(minute="*/1"),

        # (Optional) Pass default arguments to the task, provided in dictionary form
        # For example, if the task function is `heartbeat(env="prod")`:
        # 'args': ('prod',),  # Pass positional arguments
        # 'kwargs': {'env': 'prod'},  # Pass keyword arguments

        # (Optional) Used to restrict the timezone in which the task is executed
        # By default, the timezone set by CELERY_TIMEZONE is used
        # 'options': {'timezone': 'UTC'},
    },
}
