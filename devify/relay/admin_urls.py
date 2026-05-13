"""Relay admin API URLs."""

from django.urls import path

from relay.views import RelayAdminConfigAPIView, RelayAdminLlmChoicesAPIView


urlpatterns = [
    path("relay/config", RelayAdminConfigAPIView.as_view(), name="relay-admin-config"),
    path(
        "relay/llm-configs",
        RelayAdminLlmChoicesAPIView.as_view(),
        name="relay-admin-llm-configs",
    ),
]

