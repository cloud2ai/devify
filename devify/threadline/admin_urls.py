"""
Admin API URLs for threadline workflow management.
"""

from django.urls import path

from threadline.views.admin import ThreadlineWorkflowConfigAPIView
from threadline.views.admin_periodic_tasks import (
    AdminPeriodicTaskSettingsAPIView,
)

urlpatterns = [
    path(
        "config/",
        ThreadlineWorkflowConfigAPIView.as_view(),
        name="threadline-config",
    ),
    path(
        "periodic-tasks/",
        AdminPeriodicTaskSettingsAPIView.as_view(),
        name="threadline-periodic-tasks",
    ),
]
