from celery import Celery
import os

# Set the Django project's settings module. This ensures Django can load
# the appropriate configuration. The 'DJANGO_SETTINGS_MODULE' environment
# variable specifies the configuration file. Here it is set to 'core.settings',
# indicating the Django configuration file is at 'core/settings.py'.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

# Create a Celery application instance. The name of the Celery application is
# 'core', which usually matches the Django project name for better association
# of tasks with the project.
app = Celery("core")

# Load Celery configuration from Django settings.
# The namespace restricts loading to settings that start with CELERY_.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Update the result backend to use Django database
app.conf.update(result_backend="django-db")

# Automatically discover all task modules registered in the Django project.
# Celery loads any tasks defined in each app's tasks.py module.
app.autodiscover_tasks()

# Register Celery worker bootstrap hooks.
import threadline.celery_bootstrap  # noqa: F401
