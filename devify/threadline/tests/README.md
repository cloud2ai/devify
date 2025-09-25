# Threadline Tests

## Directory Structure

```
tests/
├── unit/                    # Unit tests for individual components
├── functional/              # Functional tests for complete workflows
│   └── test_eml_parsing.py # EML email parsing tests
├── api/                     # REST API endpoint tests
├── integration/             # Integration tests
├── performance/             # Performance tests
└── fixtures/                # Test data and configuration
    ├── eml_samples/         # EML test files
    ├── conftest.py          # Pytest fixtures
    └── factories.py         # Factory Boy factories
```

## Running Tests

### Using Nox (Recommended)

```bash
# EML email parsing tests
nox -s eml_tests

# All tests
nox -s tests

# Specific test categories
nox -s unit_tests
nox -s functional_tests
nox -s api_tests

# Coverage report
nox -s coverage
```

### Using Pytest Directly

```bash
# EML parsing tests
pytest functional/test_eml_parsing.py -v

# All tests
pytest -v

# Specific categories
pytest unit/ -v
pytest api/ -v
```

## Test Markers

- `@pytest.mark.unit` - Unit tests
- `@pytest.mark.functional` - Functional tests
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.performance` - Performance tests
- `@pytest.mark.django_db` - Tests requiring database

## Adding EML Tests

1. Place `.eml` file in `fixtures/eml_samples/`
2. Create corresponding `.eml.json` with expected results
3. Run `nox -s eml_tests` to validate
