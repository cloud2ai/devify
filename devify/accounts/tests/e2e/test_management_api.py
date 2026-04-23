import pytest
from django.conf import settings
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.test import APIClient

from threadline.models import EmailAlias, Settings as ThreadlineSettings


@pytest.mark.django_db
@pytest.mark.e2e
def test_management_create_user_bootstraps_related_resources():
    """Management API should bootstrap all user resources."""
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

    assert response.status_code == 201

    user = User.objects.get(username="managed-user")
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
    assert profile.language == "zh-CN"
    assert profile.timezone == "Asia/Shanghai"
    assert alias.alias == "managed-user"
    assert alias.full_email_address() == (
        f"managed-user@{settings.AUTO_ASSIGN_EMAIL_DOMAIN}"
    )
    assert prompt_config.value["language"] == "zh-CN"
    assert prompt_config.value["scene"] == settings.DEFAULT_SCENE
    assert email_config.value == {"mode": "auto_assign"}


@pytest.mark.django_db
@pytest.mark.e2e
def test_management_list_users_returns_serialized_payloads():
    """Management API should serialize user rows, not None."""
    admin_user = User.objects.create_superuser(
        username="admin-user",
        email="admin@example.com",
        password="secret12345",
    )
    User.objects.create_user(
        username="listed-user",
        email="listed@example.com",
        password="secret12345",
        first_name="Listed",
        last_name="User",
    )

    client = APIClient()
    client.force_authenticate(user=admin_user)

    response = client.get(reverse("management-users"), {"page_size": 10})

    assert response.status_code == 200

    payload = response.json()
    assert payload["count"] == 2
    assert len(payload["results"]) == 2
    assert all(item is not None for item in payload["results"])
    usernames = {item["username"] for item in payload["results"]}
    assert usernames == {"admin-user", "listed-user"}
