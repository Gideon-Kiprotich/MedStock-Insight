---
name: medstock-engineering
description: Engineering architecture, data, ML, API, security, testing, and implementation rules for the MedStock Insight final-year project. Use this skill whenever implementing, modifying, reviewing, testing, or designing the MedStock Insight system.
---

# MedStock Insight Engineering Skill

## 1. Project identity

Product:
MedStock Insight

Academic project:
A Machine Learning-Based Decision Support System for Medicine Demand Forecasting, Stockout Risk Assessment, and Inter-Facility Redistribution in the Kenyan Health-Supply-Chain Context.

This is a university final-year software engineering project.

The system is an operational supply-chain decision-support system.

It is NOT:

* a clinical decision-support system
* a prescribing system
* a diagnosis system
* an automated procurement system
* an automated physical transfer system
* a replacement for human supply-chain decisions
* a national health-system integration project

Use simulated or anonymized data unless explicitly provided with approved real data.

## 2. Core workflow

The canonical workflow is:

Inventory
→ Historical Consumption
→ Demand Forecast
→ Projected Inventory
→ Stockout Risk
→ Shortage Detection
→ Surplus Detection
→ Redistribution Recommendation
→ Human Review
→ Approve/Reject
→ Transfer Tracking

Do not introduce architectural changes that contradict this workflow without explicitly documenting the reason.

## 3. System architecture

The core ML/decision architecture is:

ML daily demand forecasting
→ deterministic projected-inventory and stockout-risk engine
→ surplus/shortage detection
→ redistribution recommendation engine
→ human approval
→ transfer execution and tracking

Forecasting is machine-learning based.

Stockout risk is primarily derived from projected inventory logic rather than being treated as a black-box ML prediction.

A secondary stockout-classification ML experiment is allowed only if it is explicitly implemented and evaluated separately.

## 4. Forecasting rules

Forecasts are generated at DAILY granularity.

7-day, 14-day, and 30-day forecast values are aggregations of daily forecast points.

Do not store only aggregate forecasts where daily forecasts are required for inventory projection.

Forecasts must be traceable to:

* forecast run
* model version
* medicine
* facility
* forecast date

Avoid data leakage.

Time-series evaluation must respect chronological ordering.

Baseline models must be retained for comparison.

Forecasting evaluation may use MAE, RMSE, and MAPE where appropriate.

Do not hard-code a specific final model such as Prophet or XGBoost unless the repository's evaluated model-selection process has explicitly established it.

## 5. Inventory source of truth

`inventory_transactions` is the authoritative inventory ledger.

Consumption is derived analytically from transaction records, especially transaction type `CONSUMPTION`.

Do not create a second authoritative consumption source that can diverge from the ledger.

Derived tables such as forecasts, risk assessments, alerts, recommendations, and reports must not become authoritative replacements for source inventory facts.

Inventory balances may be maintained as derived/current-state representations but must remain consistent with the transaction ledger.

## 6. Stockout risk rules

The stockout risk engine should consider, where available:

* current stock
* projected daily demand
* safety stock
* lead time
* confirmed incoming stock
* forecast horizon
* projected inventory trajectory

Project thresholds are:

CRITICAL:
active stockout OR projected breach within 5 days

HIGH:
projected breach in 6–10 days

MEDIUM:
projected breach in 11–15 days

LOW:
no breach within the forecast horizon

These thresholds are project-defined operational thresholds, not Kenyan clinical or regulatory standards.

Always distinguish source facts from projections.

Never present projected quantities as confirmed inventory.

## 7. Redistribution rules

Redistribution recommendations are recommendations only.

They require human approval.

The system must never silently execute a physical transfer merely because a recommendation exists.

A source facility must retain the required safety stock.

A destination shortage calculation must account for confirmed incoming stock where appropriate.

Recommendations must consider:

* source facility
* destination facility
* medicine
* available surplus
* destination shortage
* safety stock
* incoming stock
* quantity
* relevant batch constraints
* compatibility/validity constraints represented in the data model

Use terminology:

* Source Facility
* Destination Facility

Do not use "optimal" unless a true optimization model has been implemented and validated.

Prefer:
"feasible recommendation"

Recommendation generation and transfer execution are separate stages.

Recommendations must be revalidated before approval and/or dispatch where required.

## 8. Transfer execution

Transfers follow a human-controlled state machine.

Expected states include:

APPROVED
→ IN_TRANSIT
→ COMPLETED

Cancellation is allowed only from explicitly permitted states.

Invalid transitions must return a suitable conflict/error response.

Transfer completion must update inventory through transactional ledger entries.

For a completed transfer:

source:
TRANSFER_OUT

destination:
TRANSFER_IN

These updates must occur transactionally.

The transfer operation must be idempotent and protected against double completion, double dispatch, duplicate inventory movements, and concurrency errors.

## 9. Database rules

Use PostgreSQL.

Use UUID primary keys where the existing schema follows this convention.

Use UTC timestamps internally and display Africa/Nairobi at the presentation layer where appropriate.

Important entities include:

roles
users
facilities
medicine_categories
medicines
suppliers
facility_medicine_policies
batches
inventory_balances
inventory_transactions
purchase_orders
purchase_order_items
stockout_events
ml_model_versions
forecast_runs
forecast_points
risk_assessments
alerts
redistribution_recommendations
redistribution_transfers
audit_logs

Optional data-ingestion entities may include:

data_import_jobs
data_import_errors

Do not create duplicate tables for concepts already represented in the existing schema.

Inspect existing migrations before modifying the database.

Never edit an already-applied migration to change history. Create a new migration.

Add appropriate indexes, foreign keys, uniqueness constraints, check constraints, and transaction safeguards.

## 10. API rules

Use versioned API paths:

`/api/v1`

Use JSON.

Use a consistent error format:

{
"error": {
"code": "ERROR_CODE",
"message": "Human-readable explanation",
"details": {}
}
}

Main API domains include:

/auth
/users
/facilities
/medicines
/inventory
/batches
/incoming-stock
/purchase-orders
/consumption
/stockouts
/models
/forecasts
/risk-assessments
/alerts
/redistributions
/transfers
/reports
/audit
/dashboard

Preserve existing API conventions instead of inventing competing patterns.

Validate permissions server-side.

Do not rely on frontend authorization alone.

## 11. Authorization

MVP roles:

Admin
Supply Chain Manager
Inventory Officer

One role per user is sufficient for the MVP unless the existing implementation has intentionally evolved beyond this.

Human approvals must be attributable to a user.

Sensitive state changes must produce audit events.

## 12. Audit trail

Important actions should be auditable, including:

* recommendation generated
* recommendation approved
* recommendation rejected
* transfer created
* transfer dispatched
* transfer completed
* transfer cancelled
* inventory transfer out
* inventory transfer in
* important administrative changes

Audit records should identify the actor, action, affected entity, timestamp, and useful contextual information.

## 13. ML engineering

ML training and experimentation are offline concerns.

Inference should be exposed through the backend/API architecture used by the application.

Do not introduce unnecessary training into ordinary request handling.

Prevent temporal leakage.

Document model version and training/evaluation context.

Synthetic data should contain realistic variation such as:

* stable demand
* seasonality
* trend
* intermittent demand
* demand spikes
* supplier delays
* stockouts
* overstock
* expiry
* facility differences
* simultaneous surplus and shortage conditions

Do not fabricate claims that a synthetic dataset represents actual Kenyan facility behavior.

## 14. Security and privacy

No patient-level clinical information is required for the MVP.

Use authentication and role-based authorization.

Validate all input.

Protect sensitive endpoints.

Do not expose secrets in source code.

Use environment variables for credentials and configuration secrets.

Do not log passwords, tokens, or other secrets.

Treat audit data and inventory data as sensitive operational data.

Follow the repository's established secure coding conventions.

## 15. Frontend principles

The frontend should distinguish:

CONFIRMED FACTS

from

PREDICTED / PROJECTED DATA

Use visual distinctions such as solid versus dashed presentation where the design system already supports this.

Never rely on color alone for status.

Use consistent operational terminology.

Avoid exposing raw ML internals on primary operational screens unless they help the user make a decision.

Technical model diagnostics may exist in secondary/admin views.

Avoid claiming "real-time" unless actual real-time synchronization has been implemented.

## 16. Technology conventions

Respect the technology stack already present in the repository.

Expected stack:

Backend:
FastAPI
Python
PostgreSQL
SQLAlchemy
Alembic
Pydantic

ML:
scikit-learn
pandas
numpy
statsmodels where time-series statistical models are used

Frontend:
React
TypeScript
Vite

Infrastructure:
Docker / Docker Compose where already configured

Do not replace major technologies merely because another framework is personally preferred.

## 17. Testing

Every meaningful backend feature requires tests.

At minimum consider:

* happy path
* validation failures
* authorization failures
* state-transition errors
* duplicate operations
* concurrency-sensitive behavior
* rollback behavior
* inventory consistency
* audit trail creation
* model/forecast traceability
* edge cases

Do not claim tests passed unless they were actually executed.

Do not claim an endpoint works unless it was actually verified.

## 18. Scope control

Prioritize the final-year-project MVP.

Avoid unnecessary:

* microservices
* Kubernetes
* event-driven infrastructure
* national integrations
* payment systems
* patient management
* clinical decision support
* automatic procurement
* fully autonomous transfer execution

Prefer a modular monolith unless the existing repository provides a justified reason for another architecture.

## 19. Implementation discipline

For every task:

1. Inspect the repository.
2. Read relevant existing models, migrations, routes, services, schemas, and tests.
3. Identify architectural dependencies.
4. Produce a concise implementation plan.
5. Implement the smallest correct change.
6. Add/update tests.
7. Run the relevant verification commands.
8. Review the resulting diff.
9. Report exactly what changed and what was verified.

Never overwrite existing architecture blindly.

Never duplicate functionality that already exists.

Never fabricate files, endpoints, migrations, models, or test results.

When uncertain, inspect the repository before making assumptions.

## 20. Final reporting

After implementation, report:

* files changed
* database changes
* API changes
* business rules implemented
* tests added
* tests actually executed
* verification results
* known limitations
* any follow-up work required

Do not report "complete" when required verification failed.

## 21. Skill usage

Apply this skill whenever working on the MedStock Insight project, including:

* backend implementation
* frontend implementation
* database changes
* ML implementation
* API design
* testing
* refactoring
* debugging
* architecture review
* code review

When a task conflicts with this skill, explicitly identify the conflict before proceeding.
