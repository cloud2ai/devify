"""Relay API URLs."""

from django.urls import path

from relay.views import (
    AppsAPIView,
    RelayDeliveryDetailAPIView,
    RelayDeliveryListAPIView,
    RelayDeliveryRetryAPIView,
    RelayEventDetailAPIView,
    RelayEventListAPIView,
    RelayEventRetryAPIView,
    RelaySubscriptionDetailAPIView,
    RelaySubscriptionListAPIView,
    RelayTestAPIView,
)


urlpatterns = [
    path("apps", AppsAPIView.as_view(), name="relay-apps"),
    path(
        "apps/relay/subscriptions",
        RelaySubscriptionListAPIView.as_view(),
        name="relay-subscriptions",
    ),
    path(
        "apps/relay/subscriptions/<int:pk>",
        RelaySubscriptionDetailAPIView.as_view(),
        name="relay-subscription-detail",
    ),
    path("apps/relay/test", RelayTestAPIView.as_view(), name="relay-test"),
    path(
        "apps/relay/events",
        RelayEventListAPIView.as_view(),
        name="relay-events",
    ),
    path(
        "apps/relay/events/<int:pk>",
        RelayEventDetailAPIView.as_view(),
        name="relay-event-detail",
    ),
    path(
        "apps/relay/deliveries",
        RelayDeliveryListAPIView.as_view(),
        name="relay-deliveries",
    ),
    path(
        "apps/relay/deliveries/<int:pk>",
        RelayDeliveryDetailAPIView.as_view(),
        name="relay-delivery-detail",
    ),
    path(
        "apps/relay/events/<int:pk>/retry",
        RelayEventRetryAPIView.as_view(),
        name="relay-event-retry",
    ),
    path(
        "apps/relay/deliveries/<int:pk>/retry",
        RelayDeliveryRetryAPIView.as_view(),
        name="relay-delivery-retry",
    ),
]
