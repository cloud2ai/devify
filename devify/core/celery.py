from celery import Celery
import logging
import os

# Configure logging for the application
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set the Django project's settings module. This ensures Django can load
# the appropriate configuration. The 'DJANGO_SETTINGS_MODULE' environment
# variable specifies the configuration file. Here it is set to 'core.settings',
# indicating the Django configuration file is at 'core/settings.py'.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

# Create a Celery application instance. The name of the Celery application is
# 'core', which usually matches the Django project name for better association
# of tasks with the project.
logger.debug("Creating Celery application instance with name: core")
app = Celery("core")

# Load Celery configuration from Django's settings file. The 'namespace="CELERY"'
# option restricts loading to settings that start with 'CELERY_'. Therefore, all
# Celery-related settings in 'core/settings.py' must begin with 'CELERY_'.
logger.info("Loading Celery configuration from Django settings")
app.config_from_object("django.conf:settings", namespace="CELERY")

# Update the result backend to use Django database
app.conf.update(
    result_backend='django-db'
)

# Automatically discover all task modules registered in the Django project.
# Celery will search for 'tasks.py' in each app and load any tasks defined there.
logger.info("Discovering tasks in registered Django applications")
app.autodiscover_tasks()
