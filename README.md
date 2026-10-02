# MedStock Insight Backend

FastAPI backend for the MedStock Insight final-year project.

## Phase 2 — Forecasting Foundation

This phase adds:

- daily consumption aggregation from `inventory_transactions`
- two forecast model definitions:
  - `MOVING_AVERAGE_7D` — operational baseline
  - `RANDOM_FOREST` — first ML model
- daily 1–90 day forecast generation
- holdout MAE calculation
- approximate lower/upper prediction bounds based on holdout residual variability
- persistent `ml_model_versions`, `forecast_runs`, and `forecast_points`
- `/api/v1/models`
- `/api/v1/forecasts`
- `/api/v1/forecasts/generate`
- deterministic simulated demo consumption history for development

Facility identities are sourced from KMHFR and medicine formulations from KEML 2023. All inventory, consumption, procurement, user accounts, and transfers are synthetic demonstration data.

## Run locally

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# Linux/macOS: source .venv/bin/activate

pip install -e ".[dev]"

docker compose up -d
alembic upgrade head
python scripts/seed.py
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/docs` for the OpenAPI UI.

Demo login:

- email: `grace.njeri.demo@medstock.example`
- password: `ChangeMe123!`

The account and password are for a local demonstration only. Never connect this seed to live facility operations.

Run `python scripts/data_quality_report.py` after seeding for measured coverage and synthetic activity counts. The seed is idempotent; use a separate empty database for a fresh simulation. See `docs/kenya-data.md` for sources and modelling assumptions.

## Forecast workflow

1. Inventory transactions provide historical consumption.
2. The forecasting service fills missing calendar days with zero consumption.
3. A baseline or ML model is evaluated on a recent holdout window.
4. The selected model is refit on the full available history.
5. Daily predictions are written to `forecast_points`.
6. The resulting forecast run records model version, training window, number of observations, and MAE.

The forecast layer does not modify inventory balances.

## Example API flow

Login first and use the returned bearer token.

```http
GET /api/v1/models
```

```http
POST /api/v1/forecasts/generate
Content-Type: application/json

{
  "facility_id": "<FACILITY-UUID>",
  "medicine_id": "<MEDICINE-UUID>",
  "model_code": "RANDOM_FOREST",
  "horizon_days": 30,
  "lookback_days": 90
}
```

The response contains the forecast run metadata and the daily forecast points.

## Testing

Forecasting unit tests can run without PostgreSQL:

```bash
pytest -q tests/test_forecasting.py
```

The full API import test requires the PostgreSQL driver and the normal project dependencies installed from `pyproject.toml`.

## Phase 3 — Stockout Risk Engine

This phase adds:

- `risk_assessments` persistence with traceability to a specific forecast run
- projected inventory simulation day by day
- safety-stock breach date and days-to-breach
- projected stockout date
- projected shortage quantity
- standardized Critical / High / Medium / Low risk levels
- confirmed incoming-stock consideration through purchase orders
- facility/medicine risk listing and detail endpoints
- deterministic risk-engine unit tests

Risk thresholds are operational prototype rules, not national or clinical standards:

- **Critical:** active stockout or safety-stock breach within 5 days
- **High:** breach in 6–10 days
- **Medium:** breach in 11–15 days
- **Low:** no breach within the selected forecast horizon

The risk engine is a decision-support calculation. It does not make procurement decisions or automatically move stock.

## Risk workflow

1. Select the latest completed daily forecast, or specify a forecast run.
2. Read current inventory and the facility-medicine safety-stock/reorder policy.
3. Add confirmed outstanding purchase-order quantities on their expected delivery dates.
4. Subtract daily forecast demand to project inventory day by day.
5. Detect safety-stock and stockout dates.
6. Persist the risk assessment with calculation version and source forecast run.

Example endpoint:

```http
POST /api/v1/risk-assessments/generate
Content-Type: application/json

{
  "facility_id": "<FACILITY-UUID>",
  "medicine_id": "<MEDICINE-UUID>"
}
```

## Design boundary

The risk engine does not create redistribution recommendations. The next phase consumes risk assessments plus multi-facility inventory to identify feasible donor/recipient pairs and generate human-review recommendations.


## Phase 4 — Redistribution Recommendations

The backend now supports multi-facility surplus/shortage detection and human-reviewed redistribution recommendations. Recommendations are calculated from current inventory, daily forecast demand, safety stock, and confirmed incoming stock for the destination. Donor surplus is conservative and uses stock on hand rather than relying on future inbound stock.

Key endpoints:
- `GET /api/v1/redistributions/inventory/surplus`
- `GET /api/v1/redistributions/inventory/shortages`
- `POST /api/v1/redistributions/recommendations/generate`
- `GET /api/v1/redistributions/recommendations`
- `GET /api/v1/redistributions/recommendations/{id}`
- `POST /api/v1/redistributions/recommendations/{id}/approve`
- `POST /api/v1/redistributions/recommendations/{id}/reject`

Approval revalidates donor stock and safety stock and expires stale recommendations after the configured review window. Actual transfer execution is intentionally kept separate from recommendation approval and is the next implementation phase.

## Phase 9 — measurable decision support

The Forecasts page compares seven-day moving average and Random Forest with a shared final 14-day temporal holdout, reporting MAE, RMSE, WAPE and observation counts only when history is sufficient. Select a forecast to see its implemented feature definitions. Stockout Risk and Redistribution expose backend-sourced explanations and preserve human approval before transfer execution.

After seeding a disposable demo database, run scripts/verify_phase9.py to check all six controlled scenarios, or scripts/evaluate_phase9.py to evaluate every synthetic facility–medicine series. See [scenario assumptions](docs/phase9_scenarios.md). These measurements describe simulated consumption and do not establish real-world accuracy.

## Phase 10 experiments

Scenario Analysis compares controlled assumptions with saved baseline inputs;
Decision Analytics and Demand Forecasts provide pooled temporal evaluation by
model, facility and medicine. All operational data remains synthetic.

See [Phase 10 assumptions and reproducibility](docs/phase10_experiments.md) for
fresh two-year seeding, evaluation commands, simulation isolation and coverage
limits. Apply the new migration with `uv run alembic upgrade head` before starting
the API. Existing seeded ledgers are preserved; use a separate empty disposable
database to generate the longer history.
