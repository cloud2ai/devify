"""
Integration tests for Internal Plan functionality

Tests cover:
- PlanViewSet filtering for internal users
- SubscriptionViewSet blocking operations for internal users
- Internal plan auto-renewal
- assign_internal_plan management command
"""

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APIClient
from rest_framework import status

from billing.models import Plan, Subscription, UserCredits
from billing.tasks import renew_expired_credits

User = get_user_model()


@pytest.mark.django_db
class TestPlanViewSetInternalUser:
    """
    Test PlanViewSet filtering for internal users
    """

    def test_internal_user_sees_plans_but_cannot_purchase(
        self, test_user_with_internal_subscription, free_plan, starter_plan, internal_plan
    ):
        """
        Internal users should see plans (except internal plan) but cannot purchase
        """
        from billing.viewsets import PlanViewSet
        from rest_framework.test import APIRequestFactory

        factory = APIRequestFactory()
        request = factory.get('/api/billing/plans')
        request.user = test_user_with_internal_subscription

        viewset = PlanViewSet()
        viewset.request = request
        queryset = viewset.get_queryset()

        plan_slugs = list(queryset.values_list('slug', flat=True))
        # Internal users can see plans but not internal plan itself
        assert 'internal' not in plan_slugs
        assert 'free' in plan_slugs
        assert 'starter' in plan_slugs
        assert queryset.count() > 0

    def test_regular_user_excludes_internal_plan(
        self, test_user_with_free_subscription, internal_plan, free_plan, starter_plan
    ):
        """
        Regular users should not see internal plans
        """
        from billing.viewsets import PlanViewSet
        from rest_framework.test import APIRequestFactory

        factory = APIRequestFactory()
        request = factory.get('/api/billing/plans')
        request.user = test_user_with_free_subscription

        viewset = PlanViewSet()
        viewset.request = request
        queryset = viewset.get_queryset()

        plan_slugs = list(queryset.values_list('slug', flat=True))
        assert 'internal' not in plan_slugs
        assert 'free' in plan_slugs
        assert 'starter' in plan_slugs

    def test_staff_user_sees_all_plans(
        self, test_user, internal_plan, free_plan, starter_plan
    ):
        """
        Staff users should see all plans including internal
        """
        from billing.viewsets import PlanViewSet
        from rest_framework.test import APIRequestFactory

        test_user.is_staff = True
        test_user.save()

        factory = APIRequestFactory()
        request = factory.get('/api/billing/plans')
        request.user = test_user

        viewset = PlanViewSet()
        viewset.request = request
        queryset = viewset.get_queryset()

        plan_slugs = list(queryset.values_list('slug', flat=True))
        assert 'internal' in plan_slugs
        assert 'free' in plan_slugs
        assert 'starter' in plan_slugs


@pytest.mark.django_db
class TestSubscriptionViewSetInternalUser:
    """
    Test SubscriptionViewSet blocking operations for internal users
    """

    def test_internal_user_cannot_create_checkout_session(
        self, test_user_with_internal_subscription
    ):
        """
        Internal users should be blocked from creating checkout session
        """
        from billing.viewsets import SubscriptionViewSet
        from rest_framework.test import APIRequestFactory
        from rest_framework.exceptions import PermissionDenied

        factory = APIRequestFactory()
        request = factory.post('/api/billing/subscriptions/create_checkout_session')
        request.user = test_user_with_internal_subscription
        request.data = {'price_id': 'test_price_id'}

        viewset = SubscriptionViewSet()
        viewset.request = request

        with pytest.raises(PermissionDenied):
            viewset._check_internal_user(request.user)

    def test_internal_user_cannot_cancel_subscription(
        self, test_user_with_internal_subscription
    ):
        """
        Internal users should be blocked from canceling subscription
        """
        from billing.viewsets import SubscriptionViewSet
        from rest_framework.test import APIRequestFactory
        from rest_framework.exceptions import PermissionDenied

        subscription = Subscription.objects.filter(
            user=test_user_with_internal_subscription,
            status='active'
        ).first()

        factory = APIRequestFactory()
        request = factory.post(f'/api/billing/subscriptions/{subscription.id}/cancel')
        request.user = test_user_with_internal_subscription

        viewset = SubscriptionViewSet()
        viewset.request = request

        with pytest.raises(PermissionDenied):
            viewset._check_internal_user(request.user)

    def test_internal_user_cannot_create_portal_session(
        self, test_user_with_internal_subscription
    ):
        """
        Internal users should be blocked from creating portal session
        """
        from billing.viewsets import SubscriptionViewSet
        from rest_framework.test import APIRequestFactory
        from rest_framework.exceptions import PermissionDenied

        factory = APIRequestFactory()
        request = factory.post('/api/billing/subscriptions/create_portal_session')
        request.user = test_user_with_internal_subscription

        viewset = SubscriptionViewSet()
        viewset.request = request

        with pytest.raises(PermissionDenied):
            viewset._check_internal_user(request.user)

    def test_regular_user_can_access_subscription_operations(
        self, test_user_with_free_subscription
    ):
        """
        Regular users should be able to access subscription operations
        """
        from billing.viewsets import SubscriptionViewSet
        from rest_framework.test import APIRequestFactory

        factory = APIRequestFactory()
        request = factory.post('/api/billing/subscriptions/create_checkout_session')
        request.user = test_user_with_free_subscription

        viewset = SubscriptionViewSet()
        viewset.request = request

        # Should not raise exception
        try:
            viewset._check_internal_user(request.user)
        except Exception:
            pytest.fail("Regular user should not be blocked")


@pytest.mark.django_db
class TestInternalPlanAutoRenewal:
    """
    Test internal plan auto-renewal
    """

    def test_internal_plan_auto_renews_credits(
        self, test_user_with_internal_subscription, internal_plan
    ):
        """
        Internal plan credits should auto-renew when expired
        """
        user = test_user_with_internal_subscription
        credits = UserCredits.objects.get(user=user, is_active=True)

        # Set period_end to past
        credits.period_end = timezone.now() - timedelta(days=1)
        credits.consumed_credits = 5000
        credits.save()

        # Run renewal task
        renew_expired_credits()

        credits.refresh_from_db()
        assert credits.base_credits == 10000
        assert credits.consumed_credits == 0
        assert credits.period_end > timezone.now()

    def test_internal_plan_renewal_uses_plan_metadata(
        self, test_user_with_internal_subscription, internal_plan
    ):
        """
        Internal plan renewal should use plan metadata for credits
        """
        user = test_user_with_internal_subscription
        credits = UserCredits.objects.get(user=user, is_active=True)

        # Update plan metadata
        internal_plan.metadata['credits_per_period'] = 20000
        internal_plan.save()

        # Set period_end to past
        credits.period_end = timezone.now() - timedelta(days=1)
        credits.save()

        # Run renewal task
        renew_expired_credits()

        credits.refresh_from_db()
        assert credits.base_credits == 20000


@pytest.mark.django_db
class TestAssignInternalPlanCommand:
    """
    Test assign_internal_plan management command
    """

    def test_create_new_internal_user(self, internal_plan, payment_provider):
        """
        Test creating a new user with internal plan
        """
        from django.core.management import call_command
        from io import StringIO
        from billing.models import Subscription, UserCredits

        out = StringIO()
        call_command(
            'assign_internal_plan',
            '--username', 'test_internal_new',
            '--email', 'test_internal_new@example.com',
            '--create-user',
            '--password', 'testpass123',
            stdout=out
        )

        user = User.objects.get(username='test_internal_new')
        subscription = Subscription.objects.get(user=user, status='active')
        credits = UserCredits.objects.get(user=user, is_active=True)

        assert subscription.plan == internal_plan
        assert subscription.plan.is_internal is True
        assert credits.base_credits == 10000

    def test_upgrade_free_user_to_internal(
        self, test_user_with_free_subscription, internal_plan
    ):
        """
        Test upgrading a free user to internal plan
        """
        from django.core.management import call_command
        from io import StringIO
        from billing.models import Subscription, UserCredits

        user = test_user_with_free_subscription

        out = StringIO()
        call_command(
            'assign_internal_plan',
            '--username', user.username,
            stdout=out
        )

        # Old subscription should be canceled
        old_sub = Subscription.objects.filter(
            user=user,
            plan__slug='free',
            status='canceled'
        ).first()
        assert old_sub is not None

        # New internal subscription should be active
        new_sub = Subscription.objects.filter(
            user=user,
            plan=internal_plan,
            status='active'
        ).first()
        assert new_sub is not None

        credits = UserCredits.objects.get(user=user, is_active=True)
        assert credits.subscription == new_sub
        assert credits.base_credits == 10000

    def test_downgrade_internal_user_to_free(
        self, test_user_with_internal_subscription, free_plan
    ):
        """
        Test downgrading an internal user to free plan
        """
        from django.core.management import call_command
        from io import StringIO
        from billing.models import Subscription, UserCredits

        user = test_user_with_internal_subscription

        out = StringIO()
        call_command(
            'assign_internal_plan',
            '--username', user.username,
            '--downgrade-to-free',
            stdout=out
        )

        # Old internal subscription should be canceled
        old_sub = Subscription.objects.filter(
            user=user,
            plan__slug='internal',
            status='canceled'
        ).first()
        assert old_sub is not None

        # New free subscription should be active
        new_sub = Subscription.objects.filter(
            user=user,
            plan=free_plan,
            status='active'
        ).first()
        assert new_sub is not None

        credits = UserCredits.objects.get(user=user, is_active=True)
        assert credits.subscription == new_sub
        assert credits.base_credits == 10

    def test_cannot_upgrade_paid_user_to_internal(
        self, test_user_with_starter_subscription
    ):
        """
        Test that paid users cannot be upgraded to internal plan
        """
        from django.core.management import call_command
        from io import StringIO
        from django.core.management.base import CommandError

        user = test_user_with_starter_subscription

        out = StringIO()
        with pytest.raises(CommandError) as exc_info:
            call_command(
                'assign_internal_plan',
                '--username', user.username,
                stdout=out
            )

        assert 'paid subscription' in str(exc_info.value).lower()
