from types import SimpleNamespace

import pytest
from django.conf import settings
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.services.registration import RegistrationService
from threadline.agents.nodes.workflow_prepare import WorkflowPrepareNode
from threadline.management.commands.process_emails import (
    Command as ProcessEmailsCommand,
)
from threadline.models import EmailAlias, Settings as ThreadlineSettings
from threadline.utils.email import EmailSaveService, EmailSource


def _unwrap_response_payload(response):
    payload = response.json()
    if isinstance(payload, dict) and "data" in payload:
        return payload["data"]
    return payload


def _assert_auto_assign_email_config(email_config):
    assert email_config == {"mode": "auto_assign"}


def _assert_oauth_email_config(email_config):
    assert email_config["mode"] == "auto_assign"
    assert "imap_config" in email_config
    assert "filter_config" in email_config


def _assert_bootstrapped_user_state(
    user,
    *,
    expected_profile_language,
    expected_profile_timezone,
    expected_prompt_language,
    expected_scene,
    expected_email_config_assertion,
):
    profile = user.profile
    alias = EmailAlias.objects.get(user=user, is_active=True)
    prompt_config = ThreadlineSettings.objects.get(
        user=user,
        key="prompt_config",
        is_active=True,
    )
    email_config = ThreadlineSettings.objects.get(
        user=user,
        key="email_config",
        is_active=True,
    )

    assert profile.registration_completed is True
    assert profile.language == expected_profile_language
    assert profile.timezone == expected_profile_timezone
    assert alias.alias == user.username
    assert alias.full_email_address() == (
        f"{user.username}@{settings.AUTO_ASSIGN_EMAIL_DOMAIN}"
    )
    assert prompt_config.value["language"] == expected_prompt_language
    assert prompt_config.value["scene"] == expected_scene
    expected_email_config_assertion(email_config.value)

    process_emails_command = ProcessEmailsCommand()
    assert process_emails_command._detect_email_source(
        email_config.value
    ) == EmailSource.FILE

    save_service = EmailSaveService()
    save_service.load_user_mappings()
    mapped_user = save_service.find_user_by_recipient(
        {
            "recipients": [
                f"{user.username}@{settings.AUTO_ASSIGN_EMAIL_DOMAIN}",
            ]
        }
    )
    assert mapped_user is not None
    assert mapped_user.id == user.id

    workflow_prepare_node = WorkflowPrepareNode()
    workflow_prepare_node.email = SimpleNamespace(
        id=1,
        user=user,
        user_id=user.id,
    )
    worker_prompt_config = workflow_prepare_node._load_prompt_config({})

    assert worker_prompt_config["language"] == expected_prompt_language
    assert worker_prompt_config["scene"] == expected_scene


def _management_scenario():
    def run():
        admin_user = User.objects.create_superuser(
            username="admin-user",
            email="admin@example.com",
            password="secret12345",
        )

        client = APIClient()
        client.force_authenticate(user=admin_user)

        response = client.post(
            reverse("management-users"),
            {
                "username": "managed-user",
                "email": "managed@example.com",
                "password": "secret12345",
                "first_name": "Managed",
                "last_name": "User",
                "is_staff": True,
                "is_active": True,
                "language": "zh-CN",
                "timezone": "Asia/Shanghai",
                "group_ids": [],
            },
            format="json",
        )

        user = User.objects.get(username="managed-user")
        return response, user

    def assert_response(payload, user):
        assert payload["username"] == user.username
        assert payload["email"] == "managed@example.com"
        assert payload["first_name"] == "Managed"
        assert payload["last_name"] == "User"
        assert payload["language"] == "zh-CN"
        assert payload["timezone"] == "Asia/Shanghai"
        assert payload["is_staff"] is True
        assert payload["is_active"] is True

    return {
        "name": "management create user",
        "run": run,
        "expected_profile_language": "zh-CN",
        "expected_profile_timezone": "Asia/Shanghai",
        "expected_prompt_language": "zh-CN",
        "expected_scene": settings.DEFAULT_SCENE,
        "expected_email_config_assertion": _assert_auto_assign_email_config,
        "assert_response": assert_response,
        "expected_status": 201,
    }


def _registration_scenario():
    def run():
        email = "registered-user@example.com"
        token, _ = RegistrationService.create_registration_token(
            email,
            "en-US",
        )

        client = APIClient()
        response = client.post(
            reverse("register_complete"),
            {
                "token": token,
                "password": "secret12345",
                "virtual_email_username": "registered-user",
                "scene": "product_issue",
                "language": "en-US",
                "timezone": "UTC",
            },
            format="json",
        )

        user = User.objects.get(email=email)
        return response, user

    def assert_response(payload, user):
        assert payload["success"] is True
        assert payload["user"]["username"] == user.username
        assert payload["user"]["email"] == user.email

    return {
        "name": "registration complete",
        "run": run,
        "expected_profile_language": "en",
        "expected_profile_timezone": "UTC",
        "expected_prompt_language": "en-US",
        "expected_scene": "product_issue",
        "expected_email_config_assertion": _assert_auto_assign_email_config,
        "assert_response": assert_response,
        "expected_status": 200,
    }


def _oauth_scenario():
    def run():
        oauth_user = User.objects.create_user(
            username="oauth-temp-user",
            email="oauth@example.com",
            password="secret12345",
        )

        client = APIClient()
        client.force_authenticate(user=oauth_user)

        response = client.post(
            reverse("oauth_complete_setup"),
            {
                "virtual_email_username": "oauth-user",
                "scene": "chat",
                "language": "zh-CN",
                "timezone": "Asia/Shanghai",
            },
            format="json",
        )

        user = User.objects.get(username="oauth-user")
        return response, user

    def assert_response(payload, user):
        assert payload["success"] is True
        assert payload["user"]["username"] == user.username
        assert payload["user"]["email"] == user.email

    return {
        "name": "oauth setup",
        "run": run,
        "expected_profile_language": "zh-hans",
        "expected_profile_timezone": "Asia/Shanghai",
        "expected_prompt_language": "zh-CN",
        "expected_scene": "chat",
        "expected_email_config_assertion": _assert_oauth_email_config,
        "assert_response": assert_response,
        "expected_status": 200,
    }


@pytest.mark.django_db
@pytest.mark.e2e
@pytest.mark.parametrize(
    "scenario_builder",
    [
        _management_scenario,
        _registration_scenario,
        _oauth_scenario,
    ],
    ids=[
        "management",
        "registration",
        "oauth",
    ],
)
def test_user_bootstrap_api_flows_cover_worker_read_paths(scenario_builder):
    """API bootstrap flows should feed worker-side read paths."""
    scenario = scenario_builder()
    response, user = scenario["run"]()
    payload = _unwrap_response_payload(response)

    assert response.status_code == scenario["expected_status"]
    scenario["assert_response"](payload, user)

    _assert_bootstrapped_user_state(
        user,
        expected_profile_language=scenario["expected_profile_language"],
        expected_profile_timezone=scenario["expected_profile_timezone"],
        expected_prompt_language=scenario["expected_prompt_language"],
        expected_scene=scenario["expected_scene"],
        expected_email_config_assertion=scenario[
            "expected_email_config_assertion"
        ],
    )
