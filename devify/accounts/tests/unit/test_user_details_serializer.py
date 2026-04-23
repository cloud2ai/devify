import pytest
from django.contrib.auth.models import User

from accounts.serializers import UserDetailsSerializer


@pytest.mark.django_db
@pytest.mark.unit
def test_user_details_serializer_exposes_staff_flags():
    """Serializer should expose staff-related flags."""
    user = User.objects.create_user(
        username="staff-user",
        email="staff@example.com",
        password="secret",
        is_staff=True,
        is_superuser=True,
    )

    data = UserDetailsSerializer(user).data

    assert data["is_staff"] is True
    assert data["is_superuser"] is True
