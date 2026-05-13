"""Relay subscription CRUD integration tests."""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status

from relay.models import RelaySubscription

from .helpers import (
    build_sample_feishu_subscription_config,
    build_sample_jira_subscription_config,
    make_test_email_address,
    make_test_label,
)


User = get_user_model()


pytestmark = [pytest.mark.django_db, pytest.mark.integration]


def _create_subscription_payload(*, target_type: str, config: dict) -> dict:
    payload = {
        "target_type": target_type,
        "name": make_test_label(target_type, "relay", "channel"),
        "enabled": True,
        "config": config,
        "strategies": {
            "auto_merge_strategy": "update",
            "manual_merge_strategy": "linked",
            "retry_issue_strategy": "update",
        },
    }
    if target_type == "feishu_bitable":
        payload["field_mappings"] = config.get("feishu_bitable", {}).get(
            "field_mappings", {}
        )
    else:
        payload["field_mappings"] = {}
    return payload


@pytest.mark.parametrize(
    ("target_type", "config_builder"),
    [
        ("jira", build_sample_jira_subscription_config),
        ("feishu_bitable", build_sample_feishu_subscription_config),
    ],
    ids=["jira", "feishu"],
)
def test_subscription_crud_round_trip(
    api_client,
    target_type,
    config_builder,
):
    user = User.objects.create_user(
        username=make_test_label("relay", "crud", target_type).replace(" ", "-").lower(),
        email=make_test_email_address("relay", "crud", target_type),
        password="secret",
    )
    api_client.force_authenticate(user=user)

    create_response = api_client.post(
        reverse("relay-subscriptions"),
        _create_subscription_payload(
            target_type=target_type,
            config=config_builder(),
        ),
        format="json",
    )
    assert create_response.status_code == status.HTTP_201_CREATED
    subscription_id = create_response.data["data"]["id"]

    list_response = api_client.get(reverse("relay-subscriptions"))
    assert list_response.status_code == status.HTTP_200_OK
    assert len(list_response.data["data"]) == 1
    assert list_response.data["data"][0]["id"] == subscription_id
    assert list_response.data["data"][0]["name"] == make_test_label(
        target_type, "relay", "channel"
    )

    updated_config = config_builder()
    if target_type == "feishu_bitable":
        updated_config["feishu_bitable"]["table_name"] = (
            "Relay Test Table Updated"
        )
    else:
        updated_config["fields"]["project_key_config"]["default"] = "ALT"

    patch_response = api_client.patch(
        reverse("relay-subscription-detail", args=[subscription_id]),
        {
            "name": make_test_label(target_type, "relay", "channel", "updated"),
            "enabled": False,
            "config": updated_config,
        },
        format="json",
    )
    assert patch_response.status_code == status.HTTP_200_OK
    assert patch_response.data["data"]["name"].endswith("updated")
    assert patch_response.data["data"]["enabled"] is False
    if target_type == "feishu_bitable":
        assert (
            patch_response.data["data"]["config"]["feishu_bitable"][
                "table_name"
            ]
            == "Relay Test Table Updated"
        )
    else:
        assert (
            patch_response.data["data"]["config"]["fields"][
                "project_key_config"
            ]["default"]
            == "ALT"
        )

    assert RelaySubscription.objects.filter(
        id=subscription_id,
        name=make_test_label(target_type, "relay", "channel", "updated"),
        enabled=False,
    ).exists()

    delete_response = api_client.delete(
        reverse("relay-subscription-detail", args=[subscription_id])
    )
    assert delete_response.status_code == status.HTTP_200_OK

    assert not RelaySubscription.objects.filter(id=subscription_id).exists()


def test_subscription_list_isolated_by_user(api_client):
    user_one = User.objects.create_user(
        username="devify-test-relay-user-one",
        email=make_test_email_address("relay", "user", "one"),
        password="secret",
    )
    user_two = User.objects.create_user(
        username="devify-test-relay-user-two",
        email=make_test_email_address("relay", "user", "two"),
        password="secret",
    )
    RelaySubscription.objects.create(
        user=user_two,
        target_type=RelaySubscription.TargetType.JIRA,
        name=make_test_label("other", "user", "channel"),
        enabled=True,
        config=build_sample_jira_subscription_config(),
        strategies={},
        field_mappings={},
    )

    api_client.force_authenticate(user=user_one)
    response = api_client.get(reverse("relay-subscriptions"))

    assert response.status_code == status.HTTP_200_OK
    assert response.data["data"] == []


def test_subscription_requires_authentication(api_client):
    response = api_client.get(reverse("relay-subscriptions"))
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
