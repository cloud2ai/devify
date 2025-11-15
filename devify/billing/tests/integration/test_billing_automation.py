"""
Integration tests for billing automation workflows

Tests cover:
- User registration and Free plan assignment
- Credit renewal for expired subscriptions
- Automatic downgrade for failed paid subscriptions
"""

import uuid
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from billing.models import Plan, Subscription, UserCredits
from billing.services.subscription_service import SubscriptionService
from billing.tasks import (
    downgrade_failed_paid_subscriptions,
    renew_expired_credits,
)

User = get_user_model()


@pytest.mark.django_db
class TestUserRegistrationFreePlan:
    """
    Test A: User registration and Free plan assignment
    """

    def test_a1_new_user_auto_assign_free_plan(
        self, test_user, free_plan
    ):
        """
        A1: Normal scenario - new user gets Free plan automatically
        """
        SubscriptionService.assign_free_plan_to_user(test_user)

        subscription = Subscription.objects.get(user=test_user)
        assert subscription.plan == free_plan
        assert subscription.status == 'active'
        assert subscription.auto_renew is True

        credits = UserCredits.objects.get(user=test_user, is_active=True)
        assert credits.base_credits == 10
        assert credits.consumed_credits == 0
        assert credits.subscription == subscription
        assert credits.period_end > timezone.now()

    def test_a2_free_plan_not_exist(self, test_user):
        """
        A2: Boundary case - Free plan does not exist
        """
        Subscription.objects.filter(plan__slug='free').delete()
        Plan.objects.filter(slug='free').delete()

        with pytest.raises(Plan.DoesNotExist):
            SubscriptionService.assign_free_plan_to_user(test_user)

    def test_a3_user_already_has_subscription(
        self, test_user_with_free_subscription, free_plan
    ):
        """
        A3: Boundary case - user already has subscription
        """
        initial_subscription = Subscription.objects.get(
            user=test_user_with_free_subscription
        )

        SubscriptionService.assign_free_plan_to_user(
            test_user_with_free_subscription
        )

        subscription_count = Subscription.objects.filter(
            user=test_user_with_free_subscription
        ).count()
        assert subscription_count == 1
        assert Subscription.objects.get(
            user=test_user_with_free_subscription
        ) == initial_subscription


@pytest.mark.django_db
class TestCreditRenewal:
    """
    Test B: Credit renewal for expired subscriptions
    """

    def test_b1_renew_free_plan_credits(self, expired_free_subscription):
        """
        B1: Free plan user - credit renewal
        """
        from billing.models import UserCredits
        from billing.tasks import renew_expired_credits

        credits = UserCredits.objects.get(user=expired_free_subscription, is_active=True)
        old_period_end = credits.period_end
        old_consumed = credits.consumed_credits

        assert old_consumed > 0
        assert credits.period_end < timezone.now()

        renew_expired_credits()

        credits.refresh_from_db()
        assert credits.consumed_credits == 0
        assert credits.base_credits == 10
        assert credits.period_end > timezone.now()
        assert credits.period_end > old_period_end
        assert credits.period_start < credits.period_end

    def test_b2_renew_starter_plan_credits(
        self, test_user, starter_plan, payment_provider
    ):
        """
        B2: Paid plan user - credit renewal with correct quota
        """
        subscription = Subscription.objects.create(
            user=test_user,
            plan=starter_plan,
            provider=payment_provider,
            status='active',
            auto_renew=True,
            current_period_start=timezone.now(),
            current_period_end=timezone.now() + timedelta(days=30),
        )

        past_time = timezone.now() - timedelta(days=1)
        credits = UserCredits.objects.create(
            user=test_user,
            subscription=subscription,
            base_credits=100,
            consumed_credits=80,
            period_start=past_time - timedelta(days=30),
            period_end=past_time,
            is_active=True,
        )

        renew_expired_credits()

        credits.refresh_from_db()
        assert credits.consumed_credits == 0
        assert credits.base_credits == 100
        assert credits.period_end > timezone.now()

    def test_b3_skip_canceled_subscription(
        self, test_user, free_plan, payment_provider
    ):
        """
        B3: Boundary case - canceled subscription should not renew
        """
        subscription = Subscription.objects.create(
            user=test_user,
            plan=free_plan,
            provider=payment_provider,
            status='canceled',
            auto_renew=False,
            current_period_start=timezone.now() - timedelta(days=30),
            current_period_end=timezone.now() - timedelta(days=1),
        )

        past_time = timezone.now() - timedelta(days=1)
        credits = UserCredits.objects.create(
            user=test_user,
            subscription=subscription,
            base_credits=10,
            consumed_credits=5,
            period_start=past_time - timedelta(days=30),
            period_end=past_time,
            is_active=True,
        )

        old_consumed = credits.consumed_credits
        old_period_end = credits.period_end

        renew_expired_credits()

        credits.refresh_from_db()
        assert credits.consumed_credits == old_consumed
        assert credits.period_end == old_period_end

    def test_b4_skip_past_due_subscription(
        self, past_due_subscription
    ):
        """
        B4: Boundary case - past_due subscription should not renew
        """
        credits = UserCredits.objects.get(user=past_due_subscription, is_active=True)
        old_consumed = credits.consumed_credits

        renew_expired_credits()

        credits.refresh_from_db()
        assert credits.consumed_credits == old_consumed

    def test_b5_skip_not_expired_subscription(
        self, test_user_with_free_subscription
    ):
        """
        B5: Boundary case - not expired subscription should skip
        """
        credits = UserCredits.objects.get(
            user=test_user_with_free_subscription,
            is_active=True
        )
        old_consumed = credits.consumed_credits
        old_period_end = credits.period_end

        renew_expired_credits()

        credits.refresh_from_db()
        assert credits.consumed_credits == old_consumed
        assert credits.period_end == old_period_end


@pytest.mark.django_db
class TestAutomaticDowngrade:
    """
    Test C: Automatic downgrade for failed paid subscriptions
    """

    def test_c1_downgrade_after_7_days(
        self, past_due_subscription, free_plan
    ):
        """
        C1: Normal scenario - downgrade after 7 days
        """
        old_subscription = Subscription.objects.get(
            user=past_due_subscription
        )
        assert old_subscription.status == 'past_due'
        assert old_subscription.plan.slug == 'starter'

        # Verify the subscription should be found by the query
        cutoff_time = timezone.now() - timedelta(days=7)
        assert old_subscription.updated_at <= cutoff_time, (
            f"Subscription updated_at {old_subscription.updated_at} "
            f"should be <= {cutoff_time}"
        )

        downgrade_failed_paid_subscriptions()

        old_subscription.refresh_from_db()
        assert old_subscription.status == 'canceled'
        assert old_subscription.auto_renew is False

        new_subscription = Subscription.objects.get(
            user=past_due_subscription,
            status='active'
        )
        assert new_subscription.plan == free_plan

        credits = UserCredits.objects.get(user=past_due_subscription, is_active=True)
        assert credits.subscription == new_subscription
        assert credits.base_credits == 10

    def test_c2_no_downgrade_before_7_days(
        self, test_user, starter_plan, payment_provider
    ):
        """
        C2: Boundary case - no downgrade before 7 days
        """
        from billing.models import Subscription, UserCredits
        from billing.tasks import downgrade_failed_paid_subscriptions

        recent_time = timezone.now() - timedelta(days=6)
        subscription = Subscription.objects.create(
            user=test_user,
            plan=starter_plan,
            provider=payment_provider,
            status='past_due',
            auto_renew=True,
            current_period_start=timezone.now() - timedelta(days=15),
            current_period_end=timezone.now() + timedelta(days=15),
        )

        Subscription.objects.filter(pk=subscription.pk).update(
            updated_at=recent_time
        )
        subscription.refresh_from_db()

        UserCredits.objects.create(
            user=test_user,
            subscription=subscription,
            base_credits=100,
            consumed_credits=50,
            period_start=timezone.now() - timedelta(days=15),
            period_end=timezone.now() + timedelta(days=15),
            is_active=True,
        )

        downgrade_failed_paid_subscriptions()

        subscription.refresh_from_db()
        assert subscription.status == 'past_due'
        assert subscription.auto_renew is True

    def test_c3_skip_free_plan_past_due(
        self, test_user, free_plan, payment_provider
    ):
        """
        C3: Boundary case - Free plan past_due should not downgrade
        """
        from billing.models import Subscription, UserCredits
        from billing.tasks import downgrade_failed_paid_subscriptions

        past_time = timezone.now() - timedelta(days=8)
        subscription = Subscription.objects.create(
            user=test_user,
            plan=free_plan,
            provider=payment_provider,
            status='past_due',
            auto_renew=True,
            current_period_start=timezone.now() - timedelta(days=15),
            current_period_end=timezone.now() + timedelta(days=15),
        )

        Subscription.objects.filter(pk=subscription.pk).update(
            updated_at=past_time
        )
        subscription.refresh_from_db()

        UserCredits.objects.create(
            user=test_user,
            subscription=subscription,
            base_credits=10,
            consumed_credits=5,
            period_start=timezone.now() - timedelta(days=15),
            period_end=timezone.now() + timedelta(days=15),
            is_active=True,
        )

        downgrade_failed_paid_subscriptions()

        subscription.refresh_from_db()
        assert subscription.status == 'past_due'

        active_subscriptions = Subscription.objects.filter(
            user=test_user,
            status='active'
        )
        assert active_subscriptions.count() == 0

    def test_c4_downgrade_exactly_7_days(
        self, test_user, starter_plan, free_plan, payment_provider
    ):
        """
        C4: Boundary case - exactly 7 days should trigger downgrade
        """
        from billing.models import Subscription, UserCredits
        from billing.tasks import downgrade_failed_paid_subscriptions

        exactly_7_days_ago = timezone.now() - timedelta(days=7)
        subscription = Subscription.objects.create(
            user=test_user,
            plan=starter_plan,
            provider=payment_provider,
            status='past_due',
            auto_renew=True,
            current_period_start=timezone.now() - timedelta(days=15),
            current_period_end=timezone.now() + timedelta(days=15),
        )

        Subscription.objects.filter(pk=subscription.pk).update(
            updated_at=exactly_7_days_ago
        )
        subscription.refresh_from_db()

        UserCredits.objects.create(
            user=test_user,
            subscription=subscription,
            base_credits=100,
            consumed_credits=50,
            period_start=timezone.now() - timedelta(days=15),
            period_end=timezone.now() + timedelta(days=15),
            is_active=True,
        )

        downgrade_failed_paid_subscriptions()

        subscription.refresh_from_db()
        assert subscription.status == 'canceled'

        new_subscription = Subscription.objects.get(
            user=test_user,
            status='active'
        )
        assert new_subscription.plan == free_plan

    def test_c5_multiple_past_due_subscriptions(
        self, free_plan, starter_plan, payment_provider
    ):
        """
        C5: Boundary case - multiple users with past_due should all downgrade
        """
        users = []
        for i in range(3):
            unique_id = str(uuid.uuid4())[:8]
            user = User.objects.create_user(
                username=f'user{i}_{unique_id}',
                email=f'user{i}_{unique_id}@example.com',
                password='testpass123',
            )
            users.append(user)

            past_time = timezone.now() - timedelta(days=8)
            subscription = Subscription.objects.create(
                user=user,
                plan=starter_plan,
                provider=payment_provider,
                status='past_due',
                auto_renew=True,
                current_period_start=timezone.now() - timedelta(days=15),
                current_period_end=timezone.now() + timedelta(days=15),
            )

            Subscription.objects.filter(pk=subscription.pk).update(
                updated_at=past_time
            )

            UserCredits.objects.create(
                user=user,
                subscription=subscription,
                base_credits=100,
                consumed_credits=50,
                period_start=subscription.current_period_start,
                period_end=subscription.current_period_end,
                is_active=True,
            )

        downgrade_failed_paid_subscriptions()

        for user in users:
            new_subscription = Subscription.objects.get(
                user=user,
                status='active'
            )
            assert new_subscription.plan == free_plan

            credits = UserCredits.objects.get(user=user, is_active=True)
            assert credits.base_credits == 10
