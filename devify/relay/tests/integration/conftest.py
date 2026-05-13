"""Integration test bootstrap for Relay."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv


def _find_repo_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "pyproject.toml").exists():
            return parent
    return current.parent


def _candidate_env_files() -> list[Path]:
    root = _find_repo_root()
    configured = os.getenv("DEVIFY_ENV_FILE")
    if configured:
        candidate = Path(configured).expanduser()
        if candidate.is_absolute():
            return [candidate]
        return [root / candidate, Path.cwd() / candidate]
    return [root / ".env.test"]


for env_file in _candidate_env_files():
    if env_file.exists():
        load_dotenv(env_file, override=False)
        break


@pytest.fixture(scope="session")
def django_db_setup():
    """Reuse the available database instead of creating a new one."""
    yield
