# Threadline Tests

## Test Classification

- `unit`: Mock-driven tests for isolated helpers, parsers, and pure logic.
- `integration`: API and workflow tests that exercise Django routes, database state, and containerized services.
- `e2e`: Reserved for true end-to-end tests that cross process or service boundaries.

## Execution Rules

- Run all tests inside the project containers.
- Do not depend on external services or local machine state outside the container.
- Prefer deterministic fixtures and database assertions for workflow coverage.

## Directory Structure

```
tests/
├── unit/                    # Unit tests for individual components
├── integration/             # API and workflow tests
├── functional/              # Functional tests for complete workflows
│   └── test_eml_parsing.py  # EML email parsing tests
├── performance/             # Performance tests
└── fixtures/                # Test data and configuration
    ├── eml_samples/         # EML test files
    ├── conftest.py          # Pytest fixtures
    └── factories.py         # Factory Boy factories
```

## Running Tests

### Using the Devify API Container

```bash
# EML parsing tests
./scripts/run-tests-in-devify-api.sh devify/threadline/tests/functional/test_eml_parsing.py -v

# All tests
./scripts/run-tests-in-devify-api.sh

# Specific categories
./scripts/run-tests-in-devify-api.sh devify/threadline/tests/unit/ -v
./scripts/run-tests-in-devify-api.sh devify/threadline/tests/integration/ -v
```

### Using A Local Env File

For integration tests that need real credentials or service endpoints,
create a local env file that is not committed, for example:

```bash
cp env.sample .env
cp env.sample .env.integration.local
```

Then point Django settings at it when running pytest inside the container:

```bash
DEVIFY_ENV_FILE=.env.integration.local ./scripts/run-tests-in-devify-api.sh devify/threadline/tests/integration/ -v
```

`DEVIFY_ENV_FILE` is optional. If it is not set, Django will also look for:
- `.env.integration.local`
- `.env.local`

in the project root, in that order.

## Test Markers

- `@pytest.mark.unit` - Unit tests
- `@pytest.mark.functional` - Functional tests
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.e2e` - Reserved for true end-to-end tests
- `@pytest.mark.performance` - Performance tests
- `@pytest.mark.django_db` - Tests requiring database

## Adding EML Tests

1. Place `.eml` file in `fixtures/eml_samples/`
2. Create corresponding `.eml.json` with expected results
3. Run `./scripts/run-tests-in-devify-api.sh devify/threadline/tests/functional/test_eml_parsing.py -v` to validate
