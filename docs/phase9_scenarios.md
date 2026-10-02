# Phase 9 demonstration scenarios

The seed is a **synthetic simulation**, not a record of inventory or transfers at the named facilities. Run it only on a disposable database after migrations. It uses seed 20260930, a 365-day relative calendar, facility/medicine-specific SHA-256 random streams, deterministic seasonality, and ledger-backed opening stock, receipts, consumption and adjustments. Re-running the seed does not overwrite existing inventory. To reset, create a fresh demo database. Dates shift with the day of seeding.

| Identifier | Facility / medicine | Expected condition |
| --- | --- | --- |
| DEMO_CRITICAL_SHORTAGE | Mbagathi / paracetamol 500 mg | 5 units; immediate safety-stock breach |
| DEMO_HIGH_RISK | Pumwani / paracetamol 500 mg | Stock above safety by about eight demand days; high-risk window |
| DEMO_SURPLUS_DONOR | Kenyatta / paracetamol 500 mg | 900 units; usable surplus after demand and safety stock |
| DEMO_REDISTRIBUTION | Kenyatta → Mbagathi / paracetamol 500 mg | Feasible recommendation pending human review |
| DEMO_NO_FEASIBLE_DONOR | Nairobi East / epinephrine 1 mg/mL | Zero stock and no source with usable surplus |
| DEMO_SAFETY_STOCK_CONSTRAINT | Kenyatta / epinephrine 1 mg/mL | Visible stock above safety but forecast demand removes usable surplus |

Run migrations and seed against a disposable database, then run scripts/verify_phase9.py to print observed outcomes. Scenario names are hypotheses until verification.

Forecast evaluation uses a fixed final 14-day temporal holdout, a minimum 42-day training period, at least 14 nonzero training and two nonzero holdout days, and one-step predictions using only earlier actuals. Both models share the split. Synthetic-series metrics do not establish real-world accuracy. No evaluation, risk, or recommendation read mutates inventory. Approval and transfer execution remain separate human actions.
