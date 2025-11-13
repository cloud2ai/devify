"""
Main pytest configuration for Billing tests

This module provides shared pytest fixtures and configuration for all
billing test categories (unit, integration tests).
"""

import os
import sys
import django
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(project_root))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

django.setup()

import pytest

from .fixtures.conftest import *
from .fixtures.factories import *
