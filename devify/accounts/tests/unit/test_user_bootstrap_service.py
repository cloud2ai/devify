from unittest.mock import patch

import pytest
from django.contrib.auth.models import User
from django.test import override_settings

from accounts.services.user_bootstrap import UserBootstrapService


@pytest.mark.django_db
@pytest.mark.unit
@override_settings(BILLING_ENABLED=True)
def test_bootstrap_user_initializes_billing_when_enabled():
    """Billing bootstrap should run when billing is enabled."""
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
