# Development Scripts Directory

This directory contains development and testing scripts that replace Poetry functionality, providing a faster testing experience.

## Available Scripts

### Test Scripts

```bash
# Basic tests
./test.sh

# Coverage tests
./test-cov.sh

# HTML coverage report
./test-html.sh

# Fast tests (exclude slow tests)
./test-fast.sh

# Unit tests only
./test-unit.sh

# Integration tests only
./test-integration.sh

# Using main script (recommended)
./dev.sh test
./dev.sh test-cov
./dev.sh test-html
```

### Script Arguments

All scripts support pytest arguments, for example:

```bash
# Run specific test file
./test.sh devify/threadline/tests/test_email_client.py

# Verbose output
./test.sh -v

# Stop on first failure
./test.sh -x

# Run last failed tests
./test.sh --lf

# Pass arguments through main script
./dev.sh test -- -v -x
```

## Advantages

- **Fast startup**: Uses python commands directly, no extra package manager overhead
- **Simple and clear**: Each script has a single purpose, easy to understand and modify
- **Good compatibility**: Uses system-installed Python environment directly
- **Poetry replacement**: Provides tox-like functionality but more lightweight

## Dependency Management

Dependencies are still managed through pyproject.toml:

```bash
# Install development dependencies (using pip)
pip install -e .[dev]

# Or using uv (faster)
uv pip install -e .[dev]
```