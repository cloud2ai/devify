"""
Integration tests for CreditsService

Tests cover:
- Credits balance queries
- Credits checking
- Period reset
- Bonus credits granting
"""

from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from billing.models import (
    CreditsTransaction,
    Subscription,
    UserCredits,
)
from billing.services.credits_service import CreditsService

User = get_user_model()


@pytest.mark.django_db
class TestCreditsUtilities:
    """
    Test utility functions for credits management
    """

    def test_get_user_credits_creates_default(self, test_user):
        """
        get_user_credits creates default credits if not exists
        """
        credits = CreditsService.get_user_credits(test_user.id)

        assert credits.user == test_user
        assert credits.base_credits > 0
        assert credits.consumed_credits == 0
        assert credits.is_active is True

    def test_get_user_credits_returns_existing(self, test_user):
        """
        get_user_credits returns existing record without creating duplicate
        """
        from billing.models import UserCredits
        from billing.services.credits_service import CreditsService

        existing = UserCredits.objects.create(
            user=test_user,
            base_credits=50,
            consumed_credits=10,
            period_start=timezone.now(),
            period_end=timezone.now() + timedelta(days=30),
        )

        credits = CreditsService.get_user_credits(test_user.id)

        assert credits.id == existing.id
        assert credits.base_credits == 50
        assert credits.consumed_credits == 10

    def test_check_credits_sufficient(self, test_user):
        """
        check_credits returns True when user has enough credits
        """
        UserCredits.objects.create(
            user=test_user,
            base_credits=10,
            consumed_credits=3,
            period_start=timezone.now(),
            period_end=timezone.now() + timedelta(days=30),
        )

        has_credits = CreditsService.check_credits(
            user_id=test_user.id,
            required_amount=5
        )

        assert has_credits is True

    def test_check_credits_insufficient(self, test_user):
        """
        check_credits returns False when user doesn't have enough
        """
        UserCredits.objects.create(
            user=test_user,
            base_credits=10,
            consumed_credits=8,
            period_start=timezone.now(),
            period_end=timezone.now() + timedelta(days=30),
        )

        has_credits = CreditsService.check_credits(
            user_id=test_user.id,
            required_amount=5
        )

        assert has_credits is False

    def test_check_credits_with_bonus(self, test_user):
        """
        check_credits considers both base and bonus credits
        """
        UserCredits.objects.create(
            user=test_user,
            base_credits=5,
            bonus_credits=10,
            consumed_credits=0,
            period_start=timezone.now(),
            period_end=timezone.now() + timedelta(days=30),
        )

        has_credits = CreditsService.check_credits(
            user_id=test_user.id,
            required_amount=12
        )

        assert has_credits is True

    def test_get_credits_balance(self, test_user):
        """
        get_credits_balance returns formatted balance data
        """
        UserCredits.objects.create(
            user=test_user,
            base_credits=10,
            bonus_credits=5,
            consumed_credits=3,
            period_start=timezone.now(),
            period_end=timezone.now() + timedelta(days=30),
        )

        balance = CreditsService.get_credits_balance(test_user.id)

        assert balance['available_credits'] == 12
        assert balance['base_credits'] == 10
        assert balance['bonus_credits'] == 5
        assert balance['consumed_credits'] == 3
        assert 'period_end' in balance


@pytest.mark.django_db
class TestResetPeriodCredits:
    """
    Test period credits reset functionality
    """

    def test_reset_period_credits_with_subscription(
        self, test_user, starter_plan, payment_provider
    ):
        """
        Reset credits to plan quota
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

        UserCredits.objects.create(
            user=test_user,
            subscription=subscription,
            base_credits=100,
            consumed_credits=80,
            period_start=timezone.now() - timedelta(days=30),
            period_end=timezone.now(),
        )

        CreditsService.reset_period_credits(test_user.id)

        credits = UserCredits.objects.get(user=test_user)
        assert credits.base_credits == 100
        assert credits.consumed_credits == 0
        assert credits.period_end > timezone.now()

    def test_reset_period_credits_no_subscription(self, test_user):
        """
        Reset credits without subscription uses defaults
        """
        UserCredits.objects.create(
            user=test_user,
            base_credits=10,
            consumed_credits=5,
            period_start=timezone.now() - timedelta(days=30),
            period_end=timezone.now(),
        )

        CreditsService.reset_period_credits(test_user.id)

        credits = UserCredits.objects.get(user=test_user)
        assert credits.base_credits == 0
        assert credits.consumed_credits == 0


@pytest.mark.django_db
class TestGrantBonusCredits:
    """
    Test bonus credits granting
    """

    def test_grant_bonus_credits_success(self, test_user):
        """
        Grant bonus credits increases bonus_credits
        """
        UserCredits.objects.create(
            user=test_user,
            base_credits=10,
            bonus_credits=0,
            consumed_credits=0,
            period_start=timezone.now(),
            period_end=timezone.now() + timedelta(days=30),
        )

        CreditsService.grant_bonus_credits(
            user_id=test_user.id,
            amount=50,
            reason='Promotional bonus',
            operator_id=1
        )

        credits = UserCredits.objects.get(user=test_user)
        assert credits.bonus_credits == 50
        assert credits.available_credits == 60

        transaction = CreditsTransaction.objects.get(
            user=test_user,
            transaction_type='bonus'
        )
        assert transaction.amount == 50
        assert transaction.reason == 'Promotional bonus'
        assert transaction.operator_id == 1

    def test_grant_bonus_credits_multiple_times(self, test_user):
        """
        Grant bonus credits multiple times accumulates
        """
        UserCredits.objects.create(
            user=test_user,
            base_credits=10,
            bonus_credits=0,
            consumed_credits=0,
            period_start=timezone.now(),
            period_end=timezone.now() + timedelta(days=30),
        )

        CreditsService.grant_bonus_credits(
            user_id=test_user.id,
            amount=20,
            reason='First bonus'
        )

        CreditsService.grant_bonus_credits(
            user_id=test_user.id,
            amount=30,
            reason='Second bonus'
        )

        credits = UserCredits.objects.get(user=test_user)
        assert credits.bonus_credits == 50
