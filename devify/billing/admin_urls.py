from django.urls import path

from billing.admin_views import (
    BillingAdminBatchGrantCreditsAPIView,
    BillingAdminConfigAPIView,
    BillingAdminOverviewAPIView,
    BillingAdminPlanDetailAPIView,
    BillingAdminPlansAPIView,
    BillingAdminPaymentsAPIView,
    BillingAdminSubscriptionsAPIView,
    BillingAdminTransactionsAPIView,
    BillingAdminUsersAPIView,
)


urlpatterns = [
    path('config', BillingAdminConfigAPIView.as_view(), name='billing-config'),
    path('overview', BillingAdminOverviewAPIView.as_view(), name='billing-overview'),
    path('users', BillingAdminUsersAPIView.as_view(), name='billing-users'),
    path(
        'users/<int:user_id>/grant',
        BillingAdminUsersAPIView.as_view(),
        name='billing-user-grant',
    ),
    path(
        'users/batch-grant',
        BillingAdminBatchGrantCreditsAPIView.as_view(),
        name='billing-users-batch-grant',
    ),
    path(
        'transactions',
        BillingAdminTransactionsAPIView.as_view(),
        name='billing-transactions',
    ),
    path(
        'payments',
        BillingAdminPaymentsAPIView.as_view(),
        name='billing-payments',
    ),
    path(
        'subscriptions',
        BillingAdminSubscriptionsAPIView.as_view(),
        name='billing-subscriptions',
    ),
    path('plans', BillingAdminPlansAPIView.as_view(), name='billing-plans'),
    path(
        'plans/<int:plan_id>',
        BillingAdminPlanDetailAPIView.as_view(),
        name='billing-plan-detail',
    ),
]
