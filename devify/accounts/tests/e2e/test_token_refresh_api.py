import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken


@pytest.mark.django_db
@pytest.mark.e2e
def test_token_refresh_returns_new_access_token():
    """Token refresh should return a usable access token."""
    user = User.objects.create_user(
        username="refresh-user",
        email="refresh@example.com",
        password="secret12345",
    )
    refresh = RefreshToken.for_user(user)

    client = APIClient()
    response = client.post(
        "/api/v1/auth/token/refresh",
        {"refresh": str(refresh)},
        format="json",
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["access"]


@pytest.mark.django_db
@pytest.mark.e2e
def test_token_refresh_access_token_can_call_protected_endpoint():
    """Refreshed access token should reach protected APIs."""
    user = User.objects.create_user(
        username="refresh-user-2",
        email="refresh2@example.com",
        password="secret12345",
    )
    refresh = RefreshToken.for_user(user)

    client = APIClient()
    refresh_response = client.post(
        "/api/v1/auth/token/refresh",
        {"refresh": str(refresh)},
        format="json",
    )

    access_token = refresh_response.json()["data"]["access"]
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")

    profile_response = client.get("/api/v1/auth/user")

    assert profile_response.status_code == 200
    profile_payload = profile_response.json()
    assert profile_payload["data"]["email"] == "refresh2@example.com"
