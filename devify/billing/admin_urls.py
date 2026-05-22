from django.urls import path

from billing.admin_views import (
    BillingAdminBatchGrantCreditsAPIView,
    BillingAdminAuditLogsAPIView,
    BillingAdminConfigAPIView,
    BillingAdminIdentityConflictsAPIView,
    BillingAdminOverviewAPIView,
    BillingAdminPaymentCheckAPIView,
    BillingAdminPlanDetailAPIView,
    BillingAdminPlansAPIView,
    BillingAdminPlanSyncStripeAPIView,
    BillingAdminPaymentsAPIView,
    BillingAdminPaymentRecordBackfillAPIView,
    BillingAdminSubscriptionsAPIView,
    BillingAdminTransactionsAPIView,
    BillingAdminUserAssignPlanAPIView,
    BillingAdminUserSyncStripeSubscriptionAPIView,
    BillingAdminUsersAPIView,
    BillingAdminUserAssignFreePlanAPIView,
)


urlpatterns = [
    path('config', BillingAdminConfigAPIView.as_view(), name='billing-config'),
    path('overview', BillingAdminOverviewAPIView.as_view(), name='billing-overview'),
    path('users', BillingAdminUsersAPIView.as_view(), name='billing-users'),
    path(
        'identity-conflicts',
        BillingAdminIdentityConflictsAPIView.as_view(),
        name='billing-identity-conflicts',
    ),
    path(
        'users/<int:user_id>/grant',
        BillingAdminUsersAPIView.as_view(),
        name='billing-user-grant',
    ),
    path(
        'users/<int:user_id>/assign-plan',
        BillingAdminUserAssignPlanAPIView.as_view(),
        name='billing-user-assign-plan',
    ),
    path(
        'users/<int:user_id>/assign-free-plan',
        BillingAdminUserAssignFreePlanAPIView.as_view(),
        name='billing-user-assign-free-plan',
    ),
    path(
        'users/<int:user_id>/sync-stripe',
        BillingAdminUserSyncStripeSubscriptionAPIView.as_view(),
        name='billing-user-sync-stripe',
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
        'audit-logs',
        BillingAdminAuditLogsAPIView.as_view(),
        name='billing-audit-logs',
    ),
    path(
        'payments',
        BillingAdminPaymentsAPIView.as_view(),
        name='billing-payments',
    ),
    path(
        'payments/backfill',
        BillingAdminPaymentRecordBackfillAPIView.as_view(),
        name='billing-payment-record-backfill',
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
    path(
        'plans/<int:plan_id>/sync-stripe',
        BillingAdminPlanSyncStripeAPIView.as_view(),
        name='billing-plan-sync-stripe',
    ),
    path(
        'payment-check',
        BillingAdminPaymentCheckAPIView.as_view(),
        name='billing-payment-check',
    ),
]
