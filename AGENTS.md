# AGENTS.md

## Project overview

MedStock Insight is a FastAPI backend for inventory management, forecasting, stockout risk, and redistribution recommendation workflows. The project uses PostgreSQL, SQLAlchemy, Alembic, Pydantic v2, and a FastAPI app organized around routers, services, schemas, and persistence models.

## Repository map

- `app/main.py`: application startup and router registration.
- `app/api/routes/`: HTTP endpoints by domain (`auth`, `forecasts`, `risk`, `redistributions`, etc.).
- `app/services/`: business logic and calculations.
- `app/models/`: SQLAlchemy models.
- `app/schemas/`: request/response DTOs.
- `app/core/`: settings, auth, security, and shared config.
- `app/db/`: database session and base metadata.
- `alembic/versions/`: schema migrations.
- `scripts/`: local bootstrap and seed scripts.
- `tests/`: pytest coverage for imports, forecasting, risk, and redistribution behavior.

## Working conventions

- Keep edits small and domain-scoped. Follow the existing router/service/model split rather than adding ad hoc logic in endpoint functions.
- If a change alters the database schema or a model contract, also update the relevant Alembic migration and verify the migration path.
- Prefer service-layer logic for calculations and validation; keep route handlers focused on request/response orchestration.
- Maintain deterministic behavior in forecasting and risk calculations. These modules are operational prototypes and tests should validate numeric outputs and edge cases.
- Demo facility and transaction data are simulated for local development and should not be treated as live operational data.
- When adding or changing endpoints, keep OpenAPI/Schemas aligned with the request and response models.

## Run and verify locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
docker compose up -d
alembic upgrade head
python scripts/seed.py
uvicorn app.main:app --reload
```

- API docs: http://127.0.0.1:8000/docs
- Demo login: `admin@medstock.local` / `ChangeMe123!`

## Testing

Run the project tests with:

```bash
pytest -q
```

Focused checks are also available:

```bash
pytest -q tests/test_forecasting.py
pytest -q tests/test_risk.py
pytest -q tests/test_redistribution.py
```

The import smoke test confirms the app bootstraps correctly:

```bash
pytest -q tests/test_imports.py
```

## Important project context

- This backend is intentionally modular: each domain feature is separated into routes, services, and persistence concerns.
- Forecasting work creates model metadata and forecast run records; the risk engine consumes those forecast results and persists risk assessments.
- Redistribution logic is a human-review workflow and should not be conflated with actual transfer execution.
- Configuration and security defaults are centralized in `app/core/` and should be preferred over ad hoc environment handling.

## When making changes

1. Identify the relevant route and service layer.
2. Check the existing schemas and models to match project conventions.
3. Add or update tests for the behavior you are changing.
4. Run the smallest relevant pytest target before finalizing the change.
5. If the change touches persistence, validate the migration story as well as application behavior.

## Relevant documentation

- [README.md](README.md)
- [pyproject.toml](pyproject.toml)

This file is intentionally concise so that coding agents can quickly understand the stack, repo structure, and verification flow without duplicating the broader project documentation.
