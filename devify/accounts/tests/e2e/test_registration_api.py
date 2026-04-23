from unittest.mock import patch

import pytest
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.services.registration import RegistrationService


@pytest.mark.django_db
@pytest.mark.e2e
def test_complete_registration_creates_a_bootstrapped_user():
    """Registration completion should create a fully bootstrapped user."""
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

    assert response.status_code == 200

    user = User.objects.get(email=email)
    assert user.profile.registration_completed is True
    assert user.profile.language == "en"
    assert user.profile.timezone == "UTC"


@pytest.mark.django_db
@pytest.mark.e2e
def test_complete_registration_rolls_back_temp_user_when_creation_fails():
    """Registration completion should preserve retry state on failure."""
    email = "failed-user@example.com"
    token, _ = RegistrationService.create_registration_token(
        email,
        "en-US",
    )

    temp_user = User.objects.get(email=email)
    temp_profile = temp_user.profile

    client = APIClient()
    with patch(
        "accounts.views.registration.RegistrationService.create_user_with_config",
        side_effect=RuntimeError("boom"),
    ):
        response = client.post(
            reverse("register_complete"),
            {
                "token": token,
                "password": "secret12345",
                "virtual_email_username": "failed-user",
                "scene": "product_issue",
                "language": "en-US",
                "timezone": "UTC",
            },
            format="json",
        )

    assert response.status_code == 500

    temp_user.refresh_from_db()
    temp_profile.refresh_from_db()

    assert User.objects.filter(email=email).exists()
    assert temp_user.profile_id == temp_profile.id
    assert temp_profile.registration_token == token
    assert temp_profile.registration_completed is False
