"""
Integration test configuration for Threadline.

Integration tests run against the existing dev environment as-is.
They must not create a separate test database or extra simulated
infrastructure.
"""

import pytest


@pytest.fixture(scope="session")
def django_db_setup():
    """Reuse the provided database instead of creating a test database."""
    yield
