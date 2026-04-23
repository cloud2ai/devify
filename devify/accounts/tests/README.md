# Accounts Tests

## Test Classification

- `unit`: Pure component tests. Use mocks or in-memory test data. Avoid real API calls and external services.
- `e2e`: End-to-end tests. Use real API requests through `APIClient` and verify final state in the database or logs.

## Execution Rules

- Run tests inside the containerized dev stack.
- Do not rely on external environments, local services outside the container, or manual browser sessions.
- Prefer table-driven scenarios for repeated API flows.

## Current Layout

- `unit/test_user_bootstrap_service.py` - unit
- `unit/test_user_details_serializer.py` - unit
- `e2e/test_management_api.py` - e2e
- `e2e/test_registration_api.py` - e2e
- `e2e/test_token_refresh_api.py` - e2e
- `e2e/test_user_bootstrap_api_flows.py` - e2e
