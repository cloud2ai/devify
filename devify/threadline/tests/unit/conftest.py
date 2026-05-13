"""
Unit test configuration for Threadline.

Unit tests that require database access reuse the existing dev
database instead of creating a separate test database.
"""

import pytest


@pytest.fixture(scope="session")
def django_db_setup():
    """Reuse the provided database instead of creating a test database."""
    yield
