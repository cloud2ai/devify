"""
Main pytest configuration for Threadline tests

This module provides shared pytest fixtures and configuration for all
test categories (unit, integration, API, performance tests).
"""

import os
import sys
import django
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Set Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'devify.core.settings')

# Configure Django
django.setup()

import pytest
from django.contrib.auth.models import User
from django.test import Client
from rest_framework.test import APIClient

# Import fixtures from the fixtures directory
from .fixtures.conftest import *
from .fixtures.factories import *


# Additional shared fixtures can be defined here
@pytest.fixture(scope="session")
def django_db_setup():
    """
    Setup test database configuration
    """
    pass


@pytest.fixture
def api_client():
    """
    API client for testing REST endpoints
    """
    return APIClient()


@pytest.fixture
def django_client():
    """
    Django test client for testing non-API endpoints
    """
    return Client()
