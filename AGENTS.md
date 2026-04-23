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

## Commit & Pull Request Guidelines
- Commit history uses short, imperative subjects such as `Improve API error handling and logging`.
- Keep each commit focused on one change set; include docs and tests when they belong to the same behavior change.
- PRs should summarize the change, list validation steps, and include screenshots for UI updates or migration notes for schema changes.

## Security & Configuration Tips
- Keep secrets in `.env` or environment-specific compose files; never commit credentials.
- Treat `ui/` as part of this repository, not a nested Git submodule or separate checkout.
- When changing Docker paths, keep `docker-compose` references rooted at this repo, such as `./ui`.
