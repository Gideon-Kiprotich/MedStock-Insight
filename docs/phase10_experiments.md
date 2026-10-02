# Phase 10: Synthetic history and isolated experiments

The permanent demonstration banner remains required:

> DEMONSTRATION ENVIRONMENT — Data shown is simulated and does not represent live facility inventory.

KMHFR/KEML entities are **REAL-WORLD REFERENCE DATA**. All balances, consumption,
orders, accounts, approvals and transfers are **SYNTHETIC OPERATIONAL DATA**.
Facility transfer eligibility is project configuration, not facility authorization.

## Deterministic historical assumptions

`scripts/seed.py` generates 730 calendar days per applicable facility/medicine pair.
The documented seed is **20260930**. Each pair receives a SHA-256-derived random
stream from the seed and its reference codes. For identical dates and catalogue,
transaction types, quantities, dates and closing balances reproduce exactly;
record UUIDs, password salts and insertion timestamps do not.

These are experimental assumptions, not measured Kenyan demand:

- Baseline: `(3 + KEML level % 4) × facility intensity × category factor × speciality
  factor`, rounded with a minimum of two units. KEML levels are reference fields;
  using them to scale synthetic demand is solely a project assumption.
- Facility intensity: KNH 2.1, Mbagathi 1.5, Mama Lucy 1.4, Pumwani 1.0, Mathari 0.9,
  National Police Service Hospital-Mbagathi 0.65. Applicability comes from the
  explicit `PROFILES` catalogue configuration, not verified facility prescribing.
- Weekday multipliers Monday–Sunday: 1.04, 1.12, 1.10, 1.06, 1.00, 0.80, 0.72.
- Annual seasonality: sine variation ±12%; gradual trend reaches approximately +8%.
- Spikes: ×2.2 on offsets 42 and 43 in every 97-day cycle. Dips: ×0.45 on offset
  20 in every 83-day cycle. Bounded daily variation: uniform 0.72–1.28.
- Receipts follow replenishment/low-stock rules. Deliberate interruptions at offsets
  150–154 and 515–521 start with ledger adjustments to zero: two stockout events
  per series. Consumption cannot exceed available inventory; zero-consumption
  observations during interruptions are **stock-constrained**, not zero demand.
- Safety stock: 12 baseline days; reorder point: 19 baseline days. Current-state
  shortage/surplus scenarios are explicit ledger adjustments; seeded forecasts
  and one completed physical transfer demonstrate the existing approval workflow.

Run on an **empty disposable database** to obtain the expanded dataset. Existing
seeded ledgers are preserved on rerun; no historical backfill or balance reset is
performed against an existing ledger. Never delete a working database to upgrade.

```bash
export DATABASE_URL=sqlite:////tmp/medstock-phase10-demo.sqlite
uv run alembic upgrade head
uv run python scripts/seed.py --as-of 2026-10-02
uv run python scripts/evaluate_phase10.py --output /tmp/medstock-phase10-report.json
```

Omit `--as-of` for a current-date demo suitable for Scenario Analysis. Historical
as-of forecasts are intentionally rejected by current-day simulations.

## Evaluation methodology

Both MA7 and Random Forest use the final **14 days** as a temporal holdout. RF is
fitted only on earlier training data; earlier observed holdout values may supply
lags for later **one-step** predictions. This is not a 14-day recursive accuracy
claim. No random train/test shuffle occurs. Minimums: 42 training days, 14 nonzero
training days, two nonzero holdout days. Insufficient rows have no metrics.

Pooled MAE is total absolute error / observation count. RMSE is the square root
of pooled squared error / count. WAPE is 100 × pooled absolute error / pooled
absolute actual consumption; it is absent for a zero denominator. Mixed medicine
units limit interpretation of pooled MAE/RMSE. No model is labelled best.

Open **Demand Forecasts → Aggregate Forecast Evaluation** or **Decision Analytics**.
`POST /api/v1/forecast-evaluation/experiments` evaluates the complete recorded
network; the latest saved results include overall, facility and medicine groups.
It may take several minutes. It writes only an analytical snapshot, not forecasts.

## Scenario Analysis

Choose facility, formulation, demand/inventory percentages and delivery delay.
A current, complete daily forecast and policy must exist; otherwise generate a
forecast first. Destination demand and opening stock are multiplied by the chosen
percentages. The delay moves outstanding confirmed destination purchase-order
arrivals; receipts moved outside the horizon are excluded. Donors remain unchanged.

The service delegates to existing risk and redistribution position calculations.
Risk shortage uses the **minimum** projected stock; recommended quantity uses
**end-of-horizon** shortage. These may differ when deliveries follow an early
stockout. Donor availability is capped by projected surplus and current stock
above safety, and requires configured transfer eligibility. Missing or stale donor
forecasts are disclosed. Feasibility is not transfer authorization or a promise
that delivery can prevent the earliest breach.

`POST /api/v1/scenarios` stores inputs, parameters, calculation version, dates,
forecast/model identifiers, results and a SHA-256 input fingerprint in the separate
`analytical_experiments` table. `GET /api/v1/scenarios/{id}` replays those saved
inputs, even if the ledger subsequently changes. The UI labels every comparison
**SIMULATION — NOT LIVE INVENTORY**. No simulation creates inventory transactions,
changes balances/forecasts, approves recommendations or executes transfers.

## Analytics and validation

`GET /api/v1/decision-analytics` exposes current stock with individual medicine
units; active stockouts, low-stock and surplus counts; saved evaluation; latest
risk distribution and projected stockouts; recommendation status/infeasibility;
transfer states; and recorded workflow activity. Forecast-based counts disclose
coverage of complete current 14-day forecasts. Risk counts use saved assessments,
which may be older than the current ledger. Operational states remain separate
from CONFIRMED / DERIVED / PREDICTED / RECOMMENDED semantic classifications.

Run `uv run pytest -q`, `npm --prefix frontend test`, and
`npm --prefix frontend run build`. Chrome verification should include comparison,
replay, responsive layout, grouping, console errors, and before/after authoritative
inventory/transfer/forecast checks. `scripts/verify_phase9.py` retains the six prior
scenario checks; `scripts/live_e2e.py` exercises live approved transfer operations
against an explicitly supplied disposable server.

For the live regression script, supply `MEDSTOCK_E2E_ADMIN_PASSWORD` and
`MEDSTOCK_E2E_OFFICER_PASSWORD` through the environment, then run
`uv run python scripts/live_e2e.py --base-url http://127.0.0.1:8000`.
Use only a disposable seeded API: this check executes inventory and transfer operations.
