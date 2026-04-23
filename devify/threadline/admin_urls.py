"""
Admin API URLs for threadline workflow management.
"""

from django.urls import path

from threadline.views.admin import ThreadlineWorkflowConfigAPIView

urlpatterns = [
    path(
        "config/",
        ThreadlineWorkflowConfigAPIView.as_view(),
        name="threadline-config",
    ),
]
