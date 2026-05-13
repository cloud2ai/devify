"""Relay integration tests that exercise real third-party services."""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status

from relay.models import RelaySubscription
from relay.services.test_attachments import BUILTIN_TEST_ATTACHMENT

from .helpers import (
    build_real_feishu_subscription_config,
    build_real_jira_subscription_config,
    build_test_snapshot,
    make_test_email_address,
    make_test_label,
)


User = get_user_model()


pytestmark = [
    pytest.mark.django_db,
    pytest.mark.integration,
    pytest.mark.external,
]


def _assert_real_delivery_response(response):
    assert response.status_code == status.HTTP_200_OK
    data = response.data["data"]
    assert data["external_id"]
    assert data["external_url"]
    assert data["attachment_count"] == 1


@pytest.mark.parametrize(
    ("scenario", "config_builder"),
    [
        (
            "jira",
            build_real_jira_subscription_config,
        ),
        (
            "feishu_bitable",
            lambda: build_real_feishu_subscription_config(token_type="bitable"),
        ),
        (
            "feishu_wiki",
            lambda: build_real_feishu_subscription_config(token_type="wiki"),
        ),
    ],
    ids=["jira", "feishu-bitable", "feishu-wiki"],
)
def test_relay_test_endpoint_runs_against_real_service(
    api_client,
    scenario,
    config_builder,
):
    user = User.objects.create_user(
        username=f"devify-test-relay-external-{scenario}",
        email=make_test_email_address("relay", "external", scenario),
        password="secret",
    )
    api_client.force_authenticate(user=user)

    subscription = RelaySubscription.objects.create(
        user=user,
        target_type=(
            RelaySubscription.TargetType.JIRA
            if scenario == "jira"
            else RelaySubscription.TargetType.FEISHU_BITABLE
        ),
        name=make_test_label(scenario, "external", "channel"),
        enabled=True,
        config=config_builder(),
        strategies={
            "auto_merge_strategy": "update",
            "manual_merge_strategy": "linked",
            "retry_issue_strategy": "update",
        },
        field_mappings={},
    )

    response = api_client.post(
        reverse("relay-test"),
        {
            "subscription_id": subscription.id,
            "artifact_snapshot": build_test_snapshot(),
            "attachments": [BUILTIN_TEST_ATTACHMENT],
        },
        format="json",
    )

    _assert_real_delivery_response(response)
