# Repository Guidelines

## Project Structure & Module Organization

MedStock Insight combines a FastAPI backend with a React/TypeScript frontend for inventory, forecasting, risk assessment, and redistribution.

- `app/api/routes/` contains endpoints; `app/services/` holds business logic; `app/models/` and `app/schemas/` define persistence and API contracts.
- `app/core/` manages configuration/security; `app/db/` manages database sessions.
- `alembic/versions/` contains migrations; `scripts/` contains database initialization and demo seeding.
- `frontend/src/` contains `pages/`, reusable `components/`, authentication `context/`, API clients, and types. Assets live in `frontend/src/assets/` and `frontend/public/`.
- Backend tests live in `tests/`; frontend tests live in `frontend/src/test/`.

## Build, Test, and Development Commands

Run backend commands from this repository root using Python 3.11+ and an activated virtual environment:

- `pip install -e ".[dev]"` installs backend and development dependencies.
- Copy `.env.example` to `.env` for initial configuration.
- `docker compose up -d` starts PostgreSQL; `alembic upgrade head` applies migrations.
- `python scripts/seed.py` populates simulated demo data.
- `uvicorn app.main:app --reload` serves the API; OpenAPI documentation is at `/docs`.
- `pytest -q` runs backend tests; `ruff check .` checks Python lint and import rules.

From `frontend/`:

- `npm ci` installs locked dependencies; `npm run dev` starts Vite.
- `npm run build` type-checks TypeScript and produces a production build.
- `npm test` runs Vitest; `npm run lint` runs Oxlint.

## Coding Style & Naming Conventions

Use four-space Python indentation, snake_case functions/modules, PascalCase classes, and type annotations. Ruff targets 100-character lines, with E501 disabled. Match existing TypeScript style: two-space indentation, camelCase variables/functions, and PascalCase component filenames such as `DashboardPage.tsx`.

Keep calculations in services and routes focused on HTTP orchestration. Update schemas and Alembic migrations when contracts or persistence change. Keep recommendation approval separate from transfer execution.

## Testing Guidelines

Use pytest with `tests/test_*.py` and `test_*` functions. Frontend tests use Vitest, Testing Library, and jsdom in `*.test.tsx` files. No coverage threshold is configured. Add regression tests for changed behavior, including deterministic calculation boundaries and transfer state transitions. Run focused tests, such as `pytest -q tests/test_risk.py`, then the relevant suite.

## Commit & Pull Request Guidelines

History contains only `Initial Setup`; no established commit convention exists. Use concise imperative subjects and domain-scoped commits. PRs should describe behavior changes, link applicable issues, report verification, and include screenshots for UI changes plus migration notes when relevant.

## Security & Configuration

Keep secrets in ignored `.env` files. Replace default credentials before nonlocal use. Demo data is simulated; never commit operational data or local database files.
