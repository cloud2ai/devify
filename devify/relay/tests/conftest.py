"""Shared pytest fixtures for Relay tests."""

from __future__ import annotations

import os
import sys
from types import SimpleNamespace
from pathlib import Path

import django
import pytest
from dotenv import load_dotenv


project_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(project_root))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

env_file = os.getenv("DEVIFY_ENV_FILE")
if env_file:
    candidate = Path(env_file).expanduser()
    if not candidate.is_absolute():
        candidate = project_root / candidate
    if candidate.exists():
        load_dotenv(candidate, override=False)
else:
    default_env_file = project_root / ".env.test"
    if default_env_file.exists():
        load_dotenv(default_env_file, override=False)

django.setup()

from rest_framework.test import APIClient


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture(autouse=True)
def _mock_jira_sdk(monkeypatch, request):
    """Keep relay unit tests off the real Jira SDK and credentials."""
    if "integration" in str(getattr(request.node, "path", request.node.fspath)):
        yield
        return

    monkeypatch.setenv("JIRA_URL", os.getenv("JIRA_URL") or "https://jira.example.com/")
    monkeypatch.setenv("JIRA_USERNAME", os.getenv("JIRA_USERNAME") or "test_user")
    monkeypatch.setenv("JIRA_PASSWORD", os.getenv("JIRA_PASSWORD") or "test_password")

    from threadline.utils.issues import jira_client as jira_client_module

    class _DummyJira:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

        def myself(self):
            return {"name": "dummy"}

        def issue(self, issue_key, *args, **kwargs):
            return SimpleNamespace(
                key=issue_key,
                fields=SimpleNamespace(
                    summary="",
                    status=SimpleNamespace(name="Open"),
                    issuetype=SimpleNamespace(name="Task"),
                    priority=None,
                    assignee=None,
                    reporter=None,
                    created="",
                    updated="",
                    description="",
                    labels=[],
                    components=[],
                    fixVersions=[],
                    comment=SimpleNamespace(comments=[]),
                    attachment=[],
                ),
                changelog=SimpleNamespace(histories=[]),
            )

        def search_issues(self, *args, **kwargs):
            return []

        def project(self, *args, **kwargs):
            return SimpleNamespace(components=[])

        def create_issue(self, *args, **kwargs):
            return SimpleNamespace(key="REQ-1")

        def update_issue(self, *args, **kwargs):
            return None

        def add_attachment(self, *args, **kwargs):
            return None

        def create_link(self, *args, **kwargs):
            return None

    monkeypatch.setattr(jira_client_module, "JIRA", _DummyJira)
    yield
