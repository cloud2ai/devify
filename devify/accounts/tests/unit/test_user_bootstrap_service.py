from unittest.mock import patch

import pytest
from django.contrib.auth.models import User

from accounts.services.user_bootstrap import UserBootstrapService
from billing.models import Subscription
from billing.tests.fixtures.factories import create_billing_plan


@pytest.mark.django_db
@pytest.mark.unit
def test_bootstrap_user_initializes_billing_when_enabled():
    """Billing bootstrap should always run during user bootstrap."""
    user = User.objects.create_user(
        username="billing-user",
        email="billing@example.com",
        password="secret12345",
    )

    with patch.object(
        UserBootstrapService,
        "_initialize_free_plan",
    ) as initialize_free_plan:
        UserBootstrapService.bootstrap_user(
            user,
            language="zh-CN",
            timezone_str="Asia/Shanghai",
            scene="chat",
            email_config=UserBootstrapService.build_auto_assign_email_config(),
            prompt_description="User prompt configuration",
            email_description="User email configuration",
            email_alias="billing-user",
        )

    initialize_free_plan.assert_called_once_with(user)


@pytest.mark.django_db
@pytest.mark.unit
def test_bootstrap_user_is_idempotent_for_free_plan_subscription():
    """Repeated bootstrap should keep a single active Free subscription."""
    user = User.objects.create_user(
        username="idempotent-user",
        email="idempotent@example.com",
        password="secret12345",
    )
    create_billing_plan(
        slug='free',
        name='Free Plan',
        monthly_price_cents=0,
        allow_self_purchase=False,
    )

    bootstrap_kwargs = {
        "language": "zh-CN",
        "timezone_str": "Asia/Shanghai",
        "scene": "chat",
        "email_config": (
            UserBootstrapService.build_auto_assign_email_config()
        ),
        "prompt_description": "User prompt configuration",
        "email_description": "User email configuration",
        "email_alias": "idempotent-user",
    }

    UserBootstrapService.bootstrap_user(user, **bootstrap_kwargs)
    UserBootstrapService.bootstrap_user(user, **bootstrap_kwargs)

    active_subscriptions = Subscription.objects.filter(
        user=user,
        status='active',
    )
    assert active_subscriptions.count() == 1
    assert active_subscriptions.get().plan.slug == 'free'
