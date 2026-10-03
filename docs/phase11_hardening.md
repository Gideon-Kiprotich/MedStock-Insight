# Phase 11: Engineering hardening and research integrity

Validation date: **2026-10-03**, Africa/Nairobi. Scope: demonstration engineering,
not production, clinical, regulatory, national-scale or real operational validation.

> DEMONSTRATION ENVIRONMENT — Data shown is simulated and does not represent live facility inventory.

## Security and authorization

Published development signing/password defaults were removed. Debug defaults to
false; tokens require a subject and expiry; wildcard CORS and unsupported signing
algorithms are rejected. Nonlocal configurations require an explicit persistent
signing key and disabled debug. PostgreSQL binds to loopback; its password and a
12-character-minimum synthetic seed password are supplied privately at runtime.
Login no longer embeds a password or trusts cached browser identity.

Actual HTTP checks cover ADMINISTRATOR, INVENTORY_OFFICER and SUPPLY_CHAIN_MANAGER,
anonymous access, forbidden actions, inactive users and token claims disagreeing
with the authoritative database role. Officers can enter stock for their assigned
facility and complete transfers for their receiving facility only. Administrative
network evaluation is restricted to administrators/managers. General transaction
entry rejects transfer movements: approval/dispatch/receipt cannot be bypassed.

JWT access tokens remain in **localStorage**, which is not secure storage and is
exposed to script access/XSS. No comprehensive penetration-test or production
security claim is made. Current changes exclude local databases, node caches,
private environment files and generated evidence. Previously published demo
credentials and the formerly tracked SQLite file remain in Git history; history
was not rewritten. Retire existing demo credentials and signing keys before any
nonlocal use; seed new disposable accounts with a separate private password.

## Data and transfer integrity

Signed inventory_transactions reconcile exactly to all **248 inventory_balances**
in each fresh PostgreSQL database and after the live workflows. Forecasts, risk,
recommendations, approval and simulations do not move stock. Dispatch decreases
source stock once; receipt increases destination stock once. Rejection and
cancellation produce no unintended movements.

The backend rejects IN_TRANSIT → CANCELLED, COMPLETED → CANCELLED,
COMPLETED → IN_TRANSIT and premature receipt. Repeated dispatch/receipt calls
remain idempotent. Three tests use real PostgreSQL locks with two concurrent
sessions, including deliberately stale ORM objects: dispatch once, receipt once,
and one successful creation per recommendation. Transfer/recommendation/balance
locks refresh cached objects; destination creation is serialized. Expired batches
are rejected at creation and dispatch without inventory changes.

Fresh PostgreSQL migration previously failed because historical revisions created
an enum explicitly and Table creation attempted it again. A migration runner guard
verifies existing enum labels and suppresses the duplicate implicit creation;
applied revisions remain unchanged. This follows the documented
[SQLAlchemy PostgreSQL ENUM lifecycle](https://docs.sqlalchemy.org/en/20/dialects/postgresql.html#sqlalchemy.dialects.postgresql.ENUM).
Both fresh databases migrated through head `20261002_analytics`.

## ML integrity and reproducibility

Two empty disposable PostgreSQL 17 databases were independently migrated and seeded
with **20260930**, the same reference catalogue and `--as-of 2026-10-03`:
**730 days**, **248 series**, **181,040 consumption observations**. Reference rows,
signed ledger quantities/dates, controlled risks/transfers and stable scenario
checksums matched exactly. The user's existing database was not reset or deleted.

Each model has 3,472 holdout observations across 248 series:

- Moving Average 7D: MAE 2.0546000658327843; RMSE 3.0962462065870593;
  WAPE 31.504533094428414%.
- Random Forest: MAE 1.6344338761202926; RMSE 2.695854116098413;
  WAPE 25.06184877396836%.

Every series was reevaluated from stored temporal inputs and metrics were pooled
independently, reproducing all reported totals. Regression tests change the current
and every later holdout target: predictions through that target remain identical.
RF fits only preceding training data; earlier holdout actuals supply later one-step
lags. These metrics do not measure recursive 14-day performance, unconstrained
clinical demand or Kenyan real-world accuracy. Mixed units limit pooled MAE/RMSE.
Model code/version/hyperparameters and source windows remain traceable.

Random UUIDs, insertion timestamps and password salts intentionally differ. The
original UUID-bearing `fingerprint` remains available for snapshot identity. The
additional `reproducibility_fingerprint` uses stable reference codes and measured
inputs; equal-quantity donor tie-breaking also uses stable codes. Both resets gave
`8e2ea3ad80c8c07328e36951583f26cda2d52b350d3b929c8022d80854641254`.
Reproducibility requires the same as-of date, configuration and library environment.

## Reference provenance and synthetic identities

All **9 facilities and 51 medicines** carry source name/URL/type/record/version,
retrieval date and verification status. Facility registry identifiers retain their
historical KMHFR provenance (retrieved 2026-09-30); KMHFR timed out during this audit,
so current registry accuracy was not reconfirmed. Recorded discrepancies, including
Aga Khan naming and Pumwani maternity-bed fields, remain explicit.

All 51 medicine name/formulation/strength/level entries were checked against
[KEML 2023, Ministry of Health document hosted by WHO](https://extranet.who.int/cpcd/sites/default/files/public_file_repository/KEN_Kenya_Kenya-Essential-Medicines-List-2023_2023.pdf).
`KEML23-*` identifies project catalogue records, not official medicine codes.
Six eligible public facilities reflect project configuration, not organizational
transfer consent; private facilities remain context references. No KEMSA/eLMIS
integration or live procurement is claimed. Six facility-assigned `@medstock.example`
accounts are invented demonstration personas; operational stock, consumption,
orders, batches, approvals, transfers and model outcomes remain synthetic.

## UI, contracts and performance

Reviewed Login, Dashboard, Inventory, Medicines/detail, Forecasts/explanations,
Risk/explanations, Redistribution/explanations, Transfers, Facilities, Audit,
Scenario Analysis, Decision Analytics, Users and existing module placeholders.
Semantic CONFIRMED/DERIVED/PREDICTED/RECOMMENDED badges remain distinct from transfer
states. Receipt/transfer rows no longer appear as observed consumption. Missing
chart dates are disclosed rather than invented. No-breach risk, proposal stock,
forecast lookback, inventory timestamps and catalogue status labels were corrected.

Audit filters now use backend action/entity codes, failures display errors, and
unsupported immutability/statutory-compliance claims were removed. Transfer creation
opens once and remains closed after refresh. Failed login retains its form/error;
new sessions open Dashboard. An unused nonexistent facility-detail API path was
removed. OpenAPI/client-path and unique-operation-ID checks pass.

Analytics prefetch directory records, avoid repeatedly attempting unavailable
forecasts, and omit per-series detail from saved aggregate summary responses.
Chrome workflow verifies explanations, approval, dispatch, receipt, audit and
scenario replay, with no blocking console errors. Simulation preserves inventory,
transfer rows and forecast runs. All 14 sidebar screens at widths 1440/768/390 have no page overflow;
wide tables scroll within their containers.

## Verification commands and results

```bash
# Supply only an explicitly disposable local phase11_ PostgreSQL URL.
export MEDSTOCK_POSTGRES_TEST_URL="$DATABASE_URL"
uv run pytest -q                    # 65 passed, including 3 PostgreSQL race tests
uv run ruff check .                # passed
npm --prefix frontend test         # 31 passed
npm --prefix frontend run build    # TypeScript + Vite passed
npm --prefix frontend run lint     # passed: 0 errors, 18 warnings
uv run python scripts/live_e2e.py --base-url http://127.0.0.1:8001
```

Live API: 17 checks passed, source −5/destination +5 for the exercised transfer.
Six controlled Phase 9 scenarios and Kenya reference/ledger checks also passed.
To repeat fresh-reset evidence, migrate/seed two empty disposable `phase11_`
databases with the same as-of date, configure `DATABASE_URL` and
`MEDSTOCK_REPRO_COMPARE_URL`, then run `uv run python scripts/verify_phase11.py`.
It independently recomputes both networks and may take several minutes. Do not use
working/live databases. Without the explicit PostgreSQL test URL, the three race
tests are skipped; SQLite results do not establish row-lock correctness.

## Defect classification and remaining observations

- **BLOCKER, fixed:** fresh PostgreSQL migration failure.
- **MAJOR, fixed:** published credential defaults, stale-object concurrent transfer
  duplication, receiving-facility scope, direct-transfer entry bypass, reset checksum
  instability and receipt quantities presented as consumption.
- **MINOR, fixed:** authentication form/session handling, creation-modal reopening,
  stale API/audit filter contracts, hidden audit errors, misleading labels, missing
  inventory timestamps and inventory and tablet risk toolbar overflow.
- **OBSERVATION:** prototype localStorage/XSS exposure; historical demo credentials;
  dated KMHFR verification; 18 React lint warnings; 780.30 kB Vite JS chunk warning;
  Starlette TestClient deprecation. Existing Consumption/Settings placeholders remain
  explicit. No visual/application blocker or major defect remains in exercised paths.

Git publication status is reported separately with the actual commit hash, push
command outcome and final working-tree state; application validation alone does
not establish that the phase was pushed.
