# Repository Guidelines

## Project Structure & Module Organization
- `devify/` contains the Django backend, split by domain such as `accounts/`, `billing/`, and `threadline/`.
- `ui/` is the Vue 3 frontend; source code lives in `ui/src/`, static assets in `ui/public/`, and build output in `ui/dist/`.
- `docker-compose.yml` and `docker-compose.dev.yml` define production and development stacks.
- Tests live alongside features, for example `devify/billing/tests/` and `devify/threadline/tests/`.

## Build, Test, and Development Commands
- `docker-compose -f docker-compose.dev.yml up -d` starts the full local stack with the backend and UI.
- `docker-compose -f docker-compose.dev.yml build` rebuilds development images after dependency or Dockerfile changes.
- `cd ui && npm install` installs frontend dependencies; `cd ui && npm run dev` starts the Vite dev server.
- `cd ui && npm run build` produces a production frontend bundle; `cd ui && npm run lint` checks and auto-fixes Vue/JS files.
- `pytest` runs the backend test suite; use `pytest devify/threadline/tests -v` for focused runs.

## Coding Style & Naming Conventions
- Python follows PEP 8 with 4-space indentation, `snake_case` for functions/modules, and `PascalCase` for classes.
- Frontend files use Prettier defaults from `ui/.prettierrc`: 2-space indentation, single quotes, no semicolons, and LF line endings.
- Keep Vue component names descriptive and multi-word; follow existing patterns under `ui/src/components/` and `ui/src/pages/`.
- Prefer small, domain-focused modules over large shared helpers.

## Testing Guidelines
- Backend tests use `pytest` with Django markers such as `@pytest.mark.django_db`, `unit`, `integration`, and `api`.
- Test files should follow `test_*.py`; classes should start with `Test*`, and test functions with `test_*`.
- Keep tests deterministic by mocking external services and network calls.
- Integration tests must run inside the existing dev container and use the provided live environment as-is; do not create new simulated isolation layers, test databases, or extra service replicas unless the user explicitly asks for them.

## Commit & Pull Request Guidelines
- Commit history uses short, imperative subjects such as `Improve API error handling and logging`.
- Keep each commit focused on one change set; include docs and tests when they belong to the same behavior change.
- PRs should summarize the change, list validation steps, and include screenshots for UI updates or migration notes for schema changes.

## Security & Configuration Tips
- Keep secrets in `.env` or environment-specific compose files; never commit credentials.
- Treat `ui/` as part of this repository, not a nested Git submodule or separate checkout.
- When changing Docker paths, keep `docker-compose` references rooted at this repo, such as `./ui`.

## Coding Principles
These supplement the repo-specific rules above.

### Think Before Coding
- State assumptions explicitly when the task is ambiguous.
- If there are multiple valid interpretations, call them out instead of choosing silently.
- Prefer asking a focused question over guessing when the outcome could change materially.
- If a simpler solution exists, say so and use it unless the user wants more.

### Simplicity First
- Implement the smallest change that solves the request.
- Do not add abstractions, configuration, or error handling for cases that are not needed.
- Avoid speculative flexibility unless the user asked for it.
- If a solution is getting large, revisit whether it can be reduced.

### Surgical Changes
- Touch only the files and code paths required by the request.
- Avoid refactoring unrelated code, formatting adjacent sections, or renaming things that are not part of the task.
- Keep the existing style unless there is a clear reason not to.
- Remove only the imports, variables, or helpers made unused by your own edits.
- When working on the frontend, split Vue pages/components early instead of letting a single SFC grow large. If a page starts combining list, detail, filters, drawers, and heavy computed logic, extract child components immediately and keep the parent as a thin state/orchestration layer.

### Goal-Driven Execution
- Turn each task into a verifiable result.
- Write or update tests that reproduce the bug or cover the requested behavior.
- Make the smallest code change that makes the test pass.
- Verify the result before finishing and report any remaining gaps clearly.
