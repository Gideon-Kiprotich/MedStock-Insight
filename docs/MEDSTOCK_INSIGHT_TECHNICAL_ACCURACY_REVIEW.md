# MedStock Insight — Independent Technical Accuracy Review

**Review date:** 2 November 2026
**Repository:** nested `medstock-insight`, branch `main`, HEAD `0215b2522f1349150a5772654a7d206a9cc136b2`
**Documents reviewed:** `docs/reference/MEDSTOCK_INSIGHT_MASTER_DOCUMENTATION.md` and `docs/reference/Medicine_Stockout_Prediction_Final_Year_Project_Proposal.docx`

> The user-specified input filename ending `_REFINED.md` was not present. The available master at the path above was used. The proposal was read from the provided DOCX. The revised copy and this report are the only deliverables created.

## Assessment and method

The master dossier is strong in breadth and preserves the approved proposal's title, objectives, research questions, planned stages and the distinction between synthetic demonstration and real-world validation. It correctly distinguishes many of the implementation milestones and reported QA evidence from work performed during this review. However, several consequential claims were inaccurate or too tentative: lead-time use in risk, the saved forecast-run MAE, donor incoming stock in redistribution, risk breach semantics, and officer facility authorization. The reviewed copy corrects these points and adds source-level qualifications.

I inspected implementation logic in the risk, redistribution, forecasting, inventory, consumption, transfer, analytics and settings services; route decorators and dependencies; ORM models; migration files; test fixtures/cases; scripts; relevant Git commits; and supplied historical/QA notes. This was static, read-only inspection. I did not run tests, connect to a database, query runtime OpenAPI, print secrets, or modify source, tests, configuration, migrations, Git history or operational data. The 2 November QA outcomes below are reported handoff evidence and are not independently reproduced here.

### Claim register

The table reviews 36 material claims/claim groups. “Confirmed with qualifications” indicates the core statement is supported but needs limits or provenance stated. “Unsupported/runtime” means repository inspection cannot establish the live or external fact.

| # | Claim reviewed | Verdict | Evidence / correction |
|---:|---|---|---|
| 1 | Formal academic title | Confirmed | Proposal DOCX title matches the master. |
| 2 | Main objective preserved | Confirmed with qualifications | Wording is preserved; implementation status must remain separate from objective achievement. |
| 3 | Seven specific objectives | Confirmed | Proposal Sections 7–9 match the transcribed objective list. |
| 4 | Six research questions | Confirmed | Proposal wording is preserved; empirical answerability remains a separate question. |
| 5 | Proposal phases versus engineering milestones | Confirmed with qualifications | The 14 proposal stages and repo milestones are distinct. Early work is bundled in `f15ac0a`; no per-feature dates can be claimed from it. |
| 6 | Migration lineage and code head | Confirmed | Linear revisions end at `20261102_settings`; source is at commit `0215b25`. |
| 7 | Configured database is at migration head | Unsupported/runtime | Handoff says current/head were both `20261102_settings`. No DB connection was made; this is attributed, not independently verified. |
| 8 | Settings module and defaults | Confirmed with qualifications | Fixed-ID singleton convention and settings values are in models/schema/service/migration. `forecast_default_horizon_days` is used when forecast request omits horizon; `reporting_default_days` is persisted/returned but has no reporting consumer in current Python source. |
| 9 | Random Forest parameters/features | Confirmed | `app/services/forecasting.py`: 200 trees, depth 12, min leaf 2, seed 42; lag 1/7, prior rolling means 7/28 and weekday. |
| 10 | MA7 operational algorithm | Confirmed with qualifications | Recursive use of preceding observations is implemented; the short internal split differs from research evaluation and does not make bounds calibrated. |
| 11 | 730-day lookback and 1–90-day horizon | Confirmed with qualifications | 730 is maximum historical lookback, not forecast horizon. Operational horizon is 1–90; settings/UI commonly select 7/14/30. |
| 12 | Saved `ForecastRun.mae` comes from operational short holdout | Inaccurate | Run persistence uses `evaluate_series()` fixed-final-14-day MAE when eligible; short internal operational holdout supplies residual spread. |
| 13 | Research evaluation methodology | Confirmed with qualifications | Fixed final 14 days, minimum training/coverage gates, RF fit on training history, walk-forward one-step holdout using only earlier actuals. This is not recursive 14-day operational forecast evaluation. |
| 14 | MAE/RMSE/WAPE and MAPE implementation | Confirmed | Comparable research evaluation implements MAE, RMSE and WAPE (omitted for zero total). MAPE is not implemented there. |
| 15 | Prediction bounds | Confirmed with qualifications | Symmetric 1.96 residual population-standard-deviation margins, lower bound clipped at zero; heuristic uncertainty bounds, not calibrated intervals. |
| 16 | `lead_time_days` drives risk assessment | Inaccurate | Model stores it; seed sets it; `generate_risk_assessment()` passes safety stock, not lead time, into `calculate_risk()`. No direct lead-time use in redistribution either. |
| 17 | Safety breach equals zero-stock breach | Inaccurate | Current stock <= safety stock sets breach at assessment date and zero days; current stock <= 0 separately sets out-of-stock. Positive stock at/below safety stock is CRITICAL but not out-of-stock. |
| 18 | Risk category boundaries | Confirmed with qualifications | CRITICAL for current zero/negative stock or breach in <=5 days; HIGH <=10; MEDIUM <=15; else LOW. These are project thresholds, not clinical standards. |
| 19 | Projected shortage measures zero-stock deficit | Inaccurate | `projected_shortage_units=max(0, safety_stock-minimum_projected)`: deficit below safety stock. |
| 20 | Dated inbound in risk projection | Confirmed with qualifications | Outstanding quantities on confirmed/partially received orders are added on expected delivery date inside forecast interval. This is not explicit lead-time modelling. |
| 21 | Donor future inbound excluded from redistribution | Inaccurate | `_get_position()` obtains dated confirmed inbound for source and destination. Such receipts affect donor projected end position/surplus. |
| 22 | Redistribution quantity calculation | Confirmed | End position = current + inbound − forecast demand; source surplus = max(end−safety,0), destination shortage = max(safety−end,0); quantity is two-decimal floored minimum. |
| 23 | Recommendation calculation is an optimizer | Inaccurate | Source selection is deterministic by largest feasible surplus with UUID tie break; quantity is feasibility arithmetic, not an optimization solver. |
| 24 | Forecast freshness enforced for recommendations | Inaccurate | Classical service chooses latest completed forecast with sufficient daily points; no current-age check. Latest risk ID may be attached without matching/freshness validation. |
| 25 | Approval revalidation | Confirmed with qualifications | Approval checks pending/expiry and relevant policy/state; it rechecks current donor balance against safety. It does not recompute recipient shortage with fresh demand/forecast. |
| 26 | Transfer state and ledger movement | Confirmed with qualifications | Create does not move stock; dispatch writes source outflow; completion writes destination inflow; cancellation is pre-transit only; repeated dispatch/complete are idempotent. |
| 27 | PostgreSQL race protection | Confirmed with qualifications | `tests/test_postgres_hardening.py` has isolated PostgreSQL fixture requiring explicit local `phase11_` DB URL; 3 target cases reported passed in handoff. SQLite alone would not prove row-lock behavior. |
| 28 | QA-prefixed transaction exclusion | Confirmed with qualifications | `analysis_transaction_filter()` excludes `QA-` (case-insensitive) references and null refs in analytics paths using it; it is a prefix convention, not a QA field. |
| 29 | QA transaction visibility in consumption log | Confirmed with qualifications | Consumption listing filters by transaction type and officer facility scope, not QA reference; QA rows remain visible in the ledger. |
| 30 | Inventory Officer facility access is enforced uniformly | Inaccurate | It is enforced for selected writes, consumption listing and receipt completion, but not consistently across authenticated read routes. |
| 31 | Reporting default is active in reports | Unsupported/runtime | Current Python source only returns/persists `reporting_default_days`; no consumer found. No UI/report runtime behavior was executed. |
| 32 | November 2 backend/frontend/Ruff/build/race results | Unsupported/runtime | User-supplied handoff reports 67 passed/3 skipped, 38 passed, clean Ruff/build, targeted 3 PostgreSQL cases. Not rerun; exact skipped IDs/logs unavailable. |
| 33 | November 2 settings and ledger live checks | Unsupported/runtime | Persistence after backend restart and 10→9 consumption / audit reconciliation are supplied handoff claims, not independently queried. |
| 34 | Selected API smoke and browser checks | Unsupported/runtime | Selected 200 responses and desktop/390×844 checks are reported by handoff; route-by-route/browser runtime was not repeated. |
| 35 | Reported current DB migration revision | Unsupported/runtime | Supplied report states current and heads both `20261102_settings`; actual configured DB remains unverified in this audit. |
| 36 | Exact current route surface | Confirmed with qualifications | Static AST count: 44 router operation decorators across 16 route modules, plus `/health` in `app/main.py`. API paths are listed in reviewed master; no runtime OpenAPI fetch performed. |

**Tally:** 7 confirmed; 15 confirmed with qualifications; 8 inaccurate; 6 unsupported or requiring runtime verification. Total: **36**.

## Objective traceability

| Proposal objective | Relevant requirement | Implemented module | Source evidence | Test/evaluation evidence | Status |
|---|---|---|---|---|---|
| 1. Analyse relevant inventory, consumption, replenishment and stockout variables | Inspect variables/data quality relevant to availability | Ledger, policy, PO, forecast/risk, synthetic/data quality | `app/services/forecasting.py`; `app/services/risk.py`; `scripts/data_quality_report.py` | Synthetic reports/scripts; no approved real operational dataset | Partial: variables represented/analyzed on synthetic operational data; independent real-data analysis absent. |
| 2. Centralized facilities, medicines, batches, transactions, consumption | Core inventory and consumption workflow | Facilities, medicines, inventory, consumption, optional transfer batch checks | `app/services/inventory.py`; `app/services/consumption.py`; `app/services/transfers.py`; routes | `tests/test_inventory.py`, consumption/transfer tests | Partial: no general batch lifecycle/admin CRUD, imports, or full catalogue editing. |
| 3. Develop/compare demand models | Daily demand forecasts compared with statistical/ML baselines | MA7, RF, persisted runs/points, evaluation | `app/services/forecasting.py`; `app/services/analytics.py` | Forecast tests, Phase 9/10 evaluation reports/scripts | Implemented and evaluated on synthetic data; external validity unestablished. |
| 4. Risk uses stock, incoming, safety stock, lead time and history | Forecast-based risk with explicit replenishment timing | Deterministic risk + dated PO receipts | `app/services/risk.py::calculate_risk`, `generate_risk_assessment`; policy model in `app/models/core.py` | `tests/test_risk.py`, controlled synthetic scenarios | Partial: lead time field is not used in risk calculation. |
| 5. Recommend constrained inter-facility redistribution | Projected shortage/surplus, source constraints and review | Candidate/recommendation, approval, transfer services | `app/services/redistribution.py`; `app/services/transfers.py` | Redistribution/transfer tests and controlled scenarios | Implemented feasibility workflow; not optimized; freshness and recipient revalidation limitations remain. |
| 6. Dashboard and alert system | Authorized presentation of forecasts, risk, surplus, recommendations | Dashboard, risk, redistribution and decision-support UI/API | `app/api/routes/dashboard.py`; `app/api/routes/decision_support.py`; frontend pages | Supplied UI QA; no alert-management API/table | Partial: dashboards/views exist, standalone persisted alerts/acknowledgment do not. |
| 7. Evaluate predictive and operational performance against forecasting/inventory baselines | Temporal predictive evaluation and conventional inventory baseline comparison | Evaluation and scenario scripts, risk/redistribution services | `app/services/analytics.py`; `scripts/evaluate_phase9.py`, `evaluate_phase10.py` | Synthetic temporal evaluation/scenarios | Partial: MA7-vs-RF exists; separate measured reorder-point/safety-stock operational baseline is not demonstrated. |

Implementation presence is not empirical effectiveness. The stated results do not establish real-world demand accuracy, causal stockout reduction, user acceptance, or national representativeness.

## High-risk findings

### 1. Lead time

The approved Objective 4 and RQ3 name replenishment lead time. `lead_time_days` is persisted in `FacilityMedicinePolicy`, but the risk-generation path does not pass it into `calculate_risk()`, and redistribution does not use it. Expected order delivery dates independently place inbound quantities on the projection timeline. Therefore state that dated receipts are modelled, but explicit lead-time-aware classification/timing is not implemented. This remains an academic objective gap.

### 2. Safety stock versus stockout

`calculate_risk()` distinguishes `currently_out_of_stock = inventory_on_hand <= 0` from `current_breach = inventory_on_hand <= safety_stock`. The latter sets breach date to assessment date. Thus stock above zero but at/below safety stock has zero days to breach and CRITICAL classification while not currently out of stock. Projected shortage counts units below safety stock, not below zero. Keep the terms separate in diagrams, result interpretation and academic measures.

### 3. Forecast generation and research evaluation

`ForecastGenerateRequest` has optional 1–90-day horizon (default from system setting in route when omitted) and 90-day default lookback (14–730 allowed). The internal short split supplies residual spread for heuristic operational bands. `ForecastRun.mae` comes from separate `evaluate_series()` evaluation on a final 14-day holdout when sufficient history exists. Research holdout predictions are one-step, conditioned on actual preceding holdout values; this does not measure recursive multi-step 14-day operational performance. Current comparative metrics are MAE, RMSE and WAPE; do not claim MAPE or present unretained results as current performance.

### 4. QA transaction filtering

The analytical filter uses a `QA-` reference-number prefix (case-insensitive), and treats null references as included. Forecast consumption aggregation and identified analytics/evaluation paths use the filter. Consumption log remains a ledger view and shows consumption entries irrespective of that prefix. There is no dedicated QA classification, uniqueness/idempotency guarantee for the reference, or general duplicate-detection rule. A real event with a `QA-` reference could be excluded, while a QA event with another prefix could be included.

### 5. Redistribution quantity and revalidation

For each position, `projected_end = current_inventory + incoming_stock - forecast_demand`; surplus is `max(projected_end - safety_stock, 0)` and shortage `max(safety_stock - projected_end, 0)`. Recommendation is capped by their minimum and floored to two decimal places. Incoming stock is counted for donor and recipient. Source selection is deterministic; no solver optimizes network-wide allocation, cost, urgency or expiry. Recommendation generation has no forecast-age check. Approval checks donor's current balance/safety and expiry but does not recompute recipient need from a fresh projection. Generation may create a partial recommendation and does not guarantee prevention of an earlier breach.

### 6. Role and facility authorization

`app/api/deps.py` obtains role authority from the database user, and role dependencies protect routes. Facility scope is a different control. Inventory Officer is explicitly clamped on consumption-list access and selected write/movement paths, but read routes including `GET /api/v1/inventory`, `/inventory/transactions`, `/forecasts`, `/risk-assessments`, `/redistributions/*`, `/transfers*`, `/dashboard`, `/audit`, decision support and scenario/decision analytics do not consistently enforce assigned facility. Generic facility/medicine/model reads are also authenticated rather than uniformly facility-limited. This is a material cross-facility read-access gap requiring code remediation. The reviewed copy lists scope as a known security limitation; don't describe all reads as scoped.

### 7. Transfer concurrency and idempotency

Transfer creation is separate from dispatch and does not change balance. Dispatch locks/reloads transfer and source balance, checks state, expiry, batch and source safety, then writes source ledger movement and audit in the transaction. Completion checks IN_TRANSIT, scopes an Inventory Officer to destination, adds destination balance/ledger/audit and optional batch movement. Repeated dispatch/complete operations are idempotent for their resulting states; cancellation is limited to pre-transit. PostgreSQL lock claims must cite `tests/test_postgres_hardening.py` and the PostgreSQL-specific fixture. Handoff reports 3 targeted cases passing. This review did not connect to or run that database test suite.

### 8. API inventory

Static inspection found 44 route-operation decorators across 16 modules plus `/health`. The major surfaces are auth, demo users, facilities, medicines, inventory balances/transactions, model versions, forecast generation/list/detail, risk generation/list/detail, redistribution recommendations/candidates, transfers, audit, consumption, settings, dashboard, forecast/risk/recommendation explanations, scenarios, forecast-evaluation experiments/aggregate and decision analytics. There is no standalone alert, purchase-order, batch lifecycle, import, general user administration or independent report CRUD surface. Use `docs/MEDSTOCK_INSIGHT_MASTER_DOCUMENTATION_TECHNICALLY_REVIEWED.md` §22 for the detailed method/path inventory. This is source-decorator inventory, not a runtime OpenAPI fetch.

### 9. Migration head versus database revision

Migration source graph ends at `20261102_settings`; supplied QA handoff reports both `alembic current` and `alembic heads` as that ID. This audit did not connect to the configured database, so call database state “reported at the checkpoint,” not independently confirmed current state.

### 10. Planned versus actual phases

The proposal’s 14 stages are the approved academic plan. The actual nested history has five commits: `f15ac0a` Initial Setup, `c2d8c38` Phase 9 validation, `2eddd1b` scenario analytics, `869df80` engineering hardening, `0215b25` Consumption Log/System Settings. Early implementation was grouped in the initial commit; transfer migrations existed before transfer APIs/services were added in later work. Keep the 14-stage plan separate from commit chronology, and do not claim a one-to-one phase mapping or invent dates for bundled features.

### 11. November 2 QA provenance

Handoff reports: backend 67 passed/3 skipped; frontend 38 passed; Ruff and build clean; three targeted PostgreSQL concurrency cases passed; settings persisted across restart; consumption transaction/balance/audit/history reconciled; selected API domains returned 200; desktop and 390×844 checks found no captured JS exceptions or horizontal overflow; QA ledger row remained visible but was excluded from analytical totals. These are user-supplied checkpoint results, not independently rerun. Exact commands, skipped test identifiers, runtime versions and complete logs were not retained. Historical Phase 11 results (65 backend, 31 frontend, etc.) are a different checkpoint and must not be merged with these numbers.

### 12. Proposal requirements implemented versus incomplete

Forecasting model comparison exists under synthetic temporal evaluation, but no real-data validation is shown. Objective 4 lead time is absent from risk. The conventional reorder-point/safety-stock baseline comparison of Objective 7/RQ6 is not demonstrated as a separate operational evaluation. The dashboard objective is partly met, but persisted alert lifecycle is absent. Inventory management exists without batch lifecycle/import/general administration. User effectiveness, operational effect and real-facility applicability need additional study.

## Other evidence limits

- The claim that reference counts/evaluation totals are “current” should retain the run/date provenance in the master. Synthetic seeded datasets are not live facility populations.
- The audit did not access Git objects beyond the reachable local history noted above or verify remote state; the nested branch is reported ahead of `origin/main` by two commits in the local checkout. This review does not alter that state.
- No secrets were read from `.env`; no source or generated environment configuration was changed.
- A current runtime OpenAPI schema, live permission behavior, live migration revision, browser behavior, and external service connectivity remain runtime matters and should be verified only in explicitly safe environments.

## Corrections made to the reviewed master copy

The reviewed copy retains the original document’s structure and detail and corrects the traceability status for Objective 4; risk threshold and safety/zero-stock semantics; definition of projected shortage; operational-versus-evaluation MAE provenance; donor future-inbound treatment; source/destination position formulas; deterministic (non-optimized) recommendation selection; forecast freshness and approval revalidation limits; and uneven officer facility scoping. It also explains the input filename discrepancy and records a source-level correction section. No application code, tests, database, migration, environment file or Git history was modified.
