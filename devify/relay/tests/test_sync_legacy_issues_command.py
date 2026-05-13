from __future__ import annotations

from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command


User = get_user_model()


@pytest.mark.django_db
@patch("relay.management.commands.sync_relay_legacy_issues.sync_legacy_issues_for_user")
def test_sync_relay_legacy_issues_command_targets_username(mock_sync):
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

    call_command("sync_relay_legacy_issues", "--username", "agione")

    mock_sync.assert_called_once_with(user)


@pytest.mark.django_db
@patch("relay.management.commands.sync_relay_legacy_issues.sync_all_legacy_issues")
def test_sync_relay_legacy_issues_command_can_sync_all(mock_sync):
    mock_sync.return_value = {
        "status": "success",
        "created": 2,
        "updated": 1,
        "skipped": 0,
    }

    call_command("sync_relay_legacy_issues", "--all")

    mock_sync.assert_called_once()
