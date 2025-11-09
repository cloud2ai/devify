from django.urls import path, include
from rest_framework.routers import DefaultRouter

from billing.viewsets import (
    PlanViewSet,
    UserCreditsViewSet,
    SubscriptionViewSet
)

router = DefaultRouter(trailing_slash=False)
router.register(r'plans', PlanViewSet, basename='plan')
router.register(r'credits', UserCreditsViewSet, basename='credits')
router.register(
    r'subscriptions',
    SubscriptionViewSet,
    basename='subscription'
)

urlpatterns = [
    path('', include(router.urls)),
    path('webhooks/stripe/', include('djstripe.urls', namespace='djstripe')),
]
