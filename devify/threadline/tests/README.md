# Threadline Tests

## Test Classification

- `unit`: Mock-driven tests for isolated helpers, parsers, and pure logic.
- `e2e`: Real API or workflow tests that exercise the full request path and validate persisted state.
- `integration`: Multi-component tests that still stay inside the containerized dev stack.

## Execution Rules

- Run all tests inside the project containers.
- Do not depend on external services or local machine state outside the container.
- Prefer deterministic fixtures and database assertions for workflow coverage.

## Directory Structure

```
tests/
├── unit/                    # Unit tests for individual components
├── e2e/                     # Real API and workflow tests
├── functional/              # Functional tests for complete workflows
│   └── test_eml_parsing.py  # EML email parsing tests
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
nox -s e2e_tests

# Legacy compatibility alias
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
pytest e2e/ -v
```

## Test Markers

- `@pytest.mark.unit` - Unit tests
- `@pytest.mark.e2e` - End-to-end tests
- `@pytest.mark.functional` - Functional tests
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.performance` - Performance tests
- `@pytest.mark.django_db` - Tests requiring database

## Adding EML Tests

1. Place `.eml` file in `fixtures/eml_samples/`
2. Create corresponding `.eml.json` with expected results
3. Run `nox -s eml_tests` to validate
