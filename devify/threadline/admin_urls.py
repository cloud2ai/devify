"""
Admin API URLs for threadline workflow management.
"""

from django.urls import path

from threadline.views.admin_conversations import (
    AdminConversationDetailAPIView,
    AdminConversationListAPIView,
    AdminConversationTaskDetailAPIView,
    AdminConversationTasksAPIView,
)
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
    path(
        "conversations/",
        AdminConversationListAPIView.as_view(),
        name="threadline-admin-conversations",
    ),
    path(
        "conversations/<uuid:uuid>/",
        AdminConversationDetailAPIView.as_view(),
        name="threadline-admin-conversation-detail",
    ),
    path(
        "conversations/<uuid:uuid>/tasks/",
        AdminConversationTasksAPIView.as_view(),
        name="threadline-admin-conversation-tasks",
    ),
    path(
        "conversations/<uuid:uuid>/tasks/<int:task_pk>/",
        AdminConversationTaskDetailAPIView.as_view(),
        name="threadline-admin-conversation-task-detail",
    ),
]
