from __future__ import annotations

from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command


User = get_user_model()


@pytest.mark.django_db
@patch("relay.management.commands.sync_relay_legacy_channels.sync_legacy_channels_for_user")
def test_sync_relay_legacy_channels_command_targets_username(mock_sync):
    user = User.objects.create_user(
        username="agione",
        email="agione@example.com",
        password="secret",
    )
    mock_sync.return_value = {
        "status": "success",
        "created": 1,
        "updated": 0,
        "skipped": 0,
    }

    call_command("sync_relay_legacy_channels", "--username", "agione")

    mock_sync.assert_called_once_with(user)


@pytest.mark.django_db
@patch("relay.management.commands.sync_relay_legacy_channels.sync_all_legacy_channels")
def test_sync_relay_legacy_channels_command_can_sync_all(mock_sync):
    mock_sync.return_value = {
        "status": "success",
        "created": 2,
        "updated": 1,
        "skipped": 0,
    }

    call_command("sync_relay_legacy_channels", "--all")

    mock_sync.assert_called_once()
