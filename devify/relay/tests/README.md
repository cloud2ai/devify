# Relay Tests

Relay tests are split into three layers:

- `unit/`: deterministic handler, strategy, and sync tests
- `integration/`: API-level CRUD and real delivery scenarios
- `e2e/`: reserved for future browser-driven flows

## Integration Environment

Relay integration tests are executed inside the running `devify-api-dev`
container. The mounted repository is available at `/opt/devify`, so the test
command should be run from there rather than from the host shell.

- Commit `.env.test.sample`
- Keep `.env.test` uncommitted
- Use the generic helper script when possible:

Example:

```bash
./scripts/run-tests-in-devify-api.sh devify/relay/tests/integration -v
```

If you need to run the command manually, execute it inside the container:

```bash
docker exec -w /opt/devify devify-api-dev pytest devify/relay/tests/integration -v
```

If you keep the file at the repository root as `.env.test`, the integration
bootstrap will load it automatically inside the container.
