# Developer Guide

This document provides essential guidelines for developers working on the Devify project.

## Project Structure

```
devify/
├── devify/                    # Main Django project
│   ├── core/                 # Core settings and configuration
│   ├── threadline/           # Threadline application
│   └── ...
├── pyproject.toml           # Project configuration (includes pytest and coverage config)
├── dev/                     # Development scripts and documentation
│   ├── DEVELOPER.md        # This file
│   ├── dev.sh              # Main development script
│   └── test-*.sh           # Individual test scripts
└── ...
```

## Development Setup

### Prerequisites

- Python 3.11+
- pip or uv (recommended, faster)

### Installation

```bash
# Install dependencies
pip install -e .[dev]
# Or using uv (faster)
uv pip install -e .[dev]

# Create .env file
cp env.sample .env
# Edit .env with your settings
```

## Testing

### Basic Commands

```bash
# Using new development scripts (recommended, faster)
./dev.sh test
./dev.sh test-cov
./dev.sh test-html

# Or use scripts directly
./test.sh
./test-cov.sh
./test-html.sh

# Traditional way (if not using dev scripts)
python -m pytest
python -m pytest --cov=devify --cov-report=html

# Run specific tests
./test.sh devify/threadline/tests/test_email_client.py
./test.sh -m "html_parsing"
./test.sh -m "not slow"
```

### Test Markers

- `unit`: Fast unit tests (currently no tests marked as unit)
- `integration`: Integration tests
- `slow`: Long-running tests
- `auth`: Authentication tests
- `django_db`: Database-required tests
- `html_parsing`: HTML parsing functionality tests

### Writing Tests

```python
# devify/threadline/tests/test_models.py
import pytest
from django.test import TestCase
from threadline.models import EmailMessage


class TestEmailMessage(TestCase):
    def test_create_email_message(self):
        email = EmailMessage.objects.create(
            subject='Test Subject',
            content='Test content',
            sender='test@example.com'
        )
        self.assertEqual(email.subject, 'Test Subject')
```

### API Testing

```python
from rest_framework.test import APITestCase
from rest_framework import status


class ThreadlineAPITest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)

    def test_get_threadlines(self):
        url = reverse('threadlines-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
```

## Code Quality

**Note**: Code quality tools are not currently installed in this project. You can install them if needed:

```bash
# Install code quality tools (optional)
pip install black isort flake8 mypy
# Or with uv
uv pip install black isort flake8 mypy

# Then use them directly:
black devify/
isort devify/
flake8 devify/
mypy devify/
```

## Common Commands

```bash
# Development scripts (recommended)
./dev.sh test                        # Basic tests
./dev.sh test-cov                    # Coverage tests
./dev.sh test-html                   # HTML coverage report
./dev.sh test-fast                   # Fast tests (exclude slow)
./dev.sh test-unit                   # Unit tests only
./dev.sh test-integration            # Integration tests only

# Pass pytest arguments
./test.sh -v                         # Verbose output
./test.sh -x                         # Stop on first failure
./test.sh --lf                       # Run last failed tests
./test.sh --reuse-db                 # Reuse test database

# Traditional way (if not using dev scripts)
python -m pytest -v
python -m pytest --cov=devify --cov-report=html
```

## Troubleshooting

### Debug Tests

```bash
# Run with debugger on failures
./test.sh --pdb
# Or traditional way
python -m pytest --pdb
```

### Common Issues

1. **Database Errors**: Check test database configuration
2. **Import Errors**: Verify PYTHONPATH and Django settings
3. **Coverage Issues**: Check `pyproject.toml` configuration

## Resources

- [pytest Documentation](https://docs.pytest.org/)
- [Django Testing Documentation](https://docs.djangoproject.com/en/stable/topics/testing/)
- [DRF Testing Guide](https://www.django-rest-framework.org/api-guide/testing/)