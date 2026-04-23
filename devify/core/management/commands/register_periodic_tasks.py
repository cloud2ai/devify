"""
Discover installed apps' periodic_tasks modules and register their schedules.
"""

import importlib
import logging

from django.conf import settings
from django.core.management.base import BaseCommand

from core.periodic_registry import TASK_REGISTRY, apply_registry

logger = logging.getLogger(__name__)


def discover_and_register():
    """Discover app periodic tasks and apply them to django_celery_beat."""
    TASK_REGISTRY.clear()

    for app in settings.INSTALLED_APPS:
        try:
            module = importlib.import_module(f"{app}.periodic_tasks")
        except ModuleNotFoundError:
            continue

        if hasattr(module, "register_periodic_tasks"):
            try:
                module.register_periodic_tasks()
            except Exception as e:
                logger.exception(
                    "register_periodic_tasks failed for app %s: %s", app, e
                )

    apply_registry()


class Command(BaseCommand):
    help = (
        "Discover all apps' periodic_tasks.register_periodic_tasks() and "
        "register entries to django_celery_beat (idempotent)."
    )

    def handle(self, *args, **options):
        discover_and_register()
        count = len(TASK_REGISTRY)
        self.stdout.write(
            self.style.SUCCESS(
                f"Registered {count} periodic task(s) to django_celery_beat."
            )
        )
