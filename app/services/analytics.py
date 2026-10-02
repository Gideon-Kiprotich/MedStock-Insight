"""Neutral pooled evaluation and operational summaries from persisted data."""

from collections import Counter, defaultdict
from datetime import date, timedelta, timezone
from math import sqrt
from uuid import UUID

import sklearn
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.core import (
    AnalyticalExperiment,
    Facility,
    FacilityMedicinePolicy,
    ForecastModelCode,
    ForecastRun,
    InventoryBalance,
    InventoryTransaction,
    InventoryTransactionType,
    Medicine,
    RedistributionRecommendation,
    RedistributionTransfer,
    RiskAssessment,
)
from app.services.experiments import capture_position, position_result, save_experiment, serialize
from app.services.forecasting import build_daily_consumption, evaluate_series


def aggregate_rows(rows: list[dict]) -> list[dict]:
    groups = defaultdict(list)
    for row in rows:
        if row["status"] == "MEASURED":
            groups[row["model"]].append(row)
    output = []
    for model, items in sorted(groups.items()):
        n = sum(r["observations"] for r in items)
        absolute = sum(r["absolute_error"] for r in items)
        actual = sum(r["actual_total"] for r in items)
        output.append(
            {
                "model": model,
                "evaluated_series": len(items),
                "observations": n,
                "mae": absolute / n,
                "rmse": sqrt(sum(r["squared_error"] for r in items) / n),
                "wape": 100 * absolute / actual if actual else None,
            }
        )
    return output


def evaluate_network(
    db: Session, user_id: UUID | None = None, start: date | None = None, end: date | None = None
) -> dict:
    end = end or date.today()
    start = start or end - timedelta(days=729)
    pairs = db.execute(
        select(
            InventoryTransaction.facility_id,
            InventoryTransaction.medicine_id,
            func.min(InventoryTransaction.transaction_date),
            func.max(InventoryTransaction.transaction_date),
        )
        .where(
            InventoryTransaction.transaction_type == InventoryTransactionType.CONSUMPTION,
            InventoryTransaction.transaction_date >= start,
            InventoryTransaction.transaction_date <= end,
        )
        .group_by(InventoryTransaction.facility_id, InventoryTransaction.medicine_id)
        .order_by(InventoryTransaction.facility_id, InventoryTransaction.medicine_id)
    ).all()
    rows, inputs = [], []
    for f, m, first, last in pairs:
        daily = build_daily_consumption(db, f, m, max(first, start), min(last, end))
        values = [v for _, v in daily]
        facility, medicine = db.get(Facility, f), db.get(Medicine, m)
        inputs.append(
            {
                "facility_id": str(f),
                "medicine_id": str(m),
                "start": daily[0][0].isoformat(),
                "values": values,
            }
        )
        for model in (ForecastModelCode.MOVING_AVERAGE_7D, ForecastModelCode.RANDOM_FOREST):
            result = evaluate_series(values, model, daily[0][0])
            errors = [a - p for a, p in zip(result.actual, result.predicted)] if result else []
            rows.append(
                {
                    "facility_id": str(f),
                    "medicine_id": str(m),
                    "facility_name": facility.name,
                    "medicine_name": f"{medicine.generic_name} {medicine.strength or ''} {medicine.dosage_form or ''}",
                    "model": model.value,
                    "status": "MEASURED" if result else "INSUFFICIENT_DATA",
                    "training_start": daily[0][0].isoformat(),
                    "training_end": daily[-15][0].isoformat() if result else None,
                    "holdout_start": daily[-14][0].isoformat() if result else None,
                    "holdout_end": daily[-1][0].isoformat() if result else None,
                    "training_observations": result.training_observations if result else 0,
                    "observations": result.observations if result else 0,
                    "mae": result.mae if result else None,
                    "rmse": result.rmse if result else None,
                    "wape": result.wape if result else None,
                    "absolute_error": sum(abs(e) for e in errors),
                    "squared_error": sum(e * e for e in errors),
                    "actual_total": sum(abs(v) for v in result.actual) if result else 0,
                }
            )

    def grouped(key, name):
        groups = defaultdict(list)
        for row in rows:
            groups[(row[key], row[name])].append(row)
        return [
            {"id": key[0], "name": key[1], "metrics": aggregate_rows(items)}
            for key, items in sorted(groups.items())
        ]

    result = {
        "overall": aggregate_rows(rows),
        "by_facility": grouped("facility_id", "facility_name"),
        "by_medicine": grouped("medicine_id", "medicine_name"),
        "results": rows,
        "series_count": len(pairs),
        "methodology": "Final 14 days, fixed temporal training, one-step predictions using only earlier actuals. Pooled MAE and RMSE weight observations; WAPE pools absolute error / absolute recorded consumption. Units differ across medicines; no model ranking or generalized accuracy claim.",
        "data_note": "SYNTHETIC OPERATIONAL DATA — recorded consumption is constrained by simulated stock availability, not unconstrained demand.",
    }
    context = {
        "version": "evaluation-1.0",
        "scikit_learn_version": sklearn.__version__,
        "inputs": inputs,
        "random_state": 42,
        "n_estimators": 200,
        "max_depth": 12,
        "min_samples_leaf": 2,
        "holdout_days": 14,
    }
    return serialize(
        save_experiment(
            db, "EVALUATION", {"start_date": start, "end_date": end}, context, result, user_id
        )
    )


def latest_evaluation(db: Session) -> dict | None:
    record = db.scalar(
        select(AnalyticalExperiment)
        .where(AnalyticalExperiment.kind == "EVALUATION")
        .order_by(AnalyticalExperiment.created_at.desc(), AnalyticalExperiment.id.desc())
        .limit(1)
    )
    if not record:
        return None
    return {
        "id": record.id,
        "created_at": record.created_at.replace(tzinfo=timezone.utc)
        if record.created_at.tzinfo is None
        else record.created_at,
        "fingerprint": record.fingerprint,
        "parameters": record.parameters,
        **record.result,
    }


def operational_summary(db: Session) -> dict:
    balances = db.scalars(select(InventoryBalance)).all()
    policies = {
        (p.facility_id, p.medicine_id): p for p in db.scalars(select(FacilityMedicinePolicy)).all()
    }
    stock, low, stockouts = [], 0, 0
    for b in balances:
        medicine, facility = db.get(Medicine, b.medicine_id), db.get(Facility, b.facility_id)
        if not medicine.is_active or not facility.is_active:
            continue
        stock.append(
            {
                "facility_id": b.facility_id,
                "medicine_id": b.medicine_id,
                "facility": facility.name,
                "medicine": f"{medicine.generic_name} {medicine.strength or ''}",
                "quantity": b.quantity_on_hand,
                "unit": medicine.unit_of_measure,
            }
        )
        stockouts += int(b.quantity_on_hand <= 0)
        p = policies.get((b.facility_id, b.medicine_id))
        low += int(p is not None and 0 < b.quantity_on_hand <= p.reorder_point)
    latest_risk = {}
    for risk in db.scalars(
        select(RiskAssessment).order_by(RiskAssessment.assessed_at, RiskAssessment.id)
    ).all():
        latest_risk[(risk.facility_id, risk.medicine_id)] = risk
    risks = Counter(r.risk_level.value for r in latest_risk.values())
    surplus, shortages, infeasible, coverage = 0, 0, 0, 0
    positions = defaultdict(list)
    for f, m in policies:
        facility = db.get(Facility, f)
        if not facility.is_active:
            continue
        try:
            snapshot = capture_position(db, facility, m, 14, date.today())
            position = position_result(snapshot, date.today())
            positions[m].append((facility, position))
            coverage += 1
            surplus += int(position["available_surplus"] > 0)
            shortages += int(position["end_shortage"] > 0)
        except HTTPException:
            continue
    for items in positions.values():
        for facility, p in items:
            if p["end_shortage"] > 0 and not (
                facility.transfer_eligible
                and any(
                    f.id != facility.id and f.transfer_eligible and q["available_surplus"] > 0
                    for f, q in items
                )
            ):
                infeasible += 1
    recommendations = db.scalars(select(RedistributionRecommendation)).all()
    transfers = db.scalars(select(RedistributionTransfer)).all()
    activity = defaultdict(lambda: {"recommendations": 0, "transfers": 0})
    for record in recommendations:
        activity[record.created_at.date().isoformat()]["recommendations"] += 1
    for record in transfers:
        activity[record.created_at.date().isoformat()]["transfers"] += 1
    return {
        "inventory": {
            "stock": stock,
            "active_stockouts": stockouts,
            "low_stock_items": low,
            "surplus_items": surplus,
            "projected_shortage_items": shortages,
            "position_coverage": coverage,
        },
        "forecasting": {
            "runs": db.scalar(select(func.count()).select_from(ForecastRun)),
            "evaluation": latest_evaluation(db),
        },
        "risk": {
            **{k: risks[k] for k in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]},
            "projected_stockouts": sum(
                r.projected_stockout_date is not None for r in latest_risk.values()
            ),
            "assessment_coverage": len(latest_risk),
        },
        "redistribution": {
            "generated": len(recommendations),
            **{
                k: sum(r.status.value == k for r in recommendations)
                for k in ["PENDING_REVIEW", "APPROVED", "REJECTED", "EXPIRED", "CANCELLED"]
            },
            "infeasible_shortage_cases": infeasible,
        },
        "transfers": {
            k: sum(t.status.value == k for t in transfers)
            for k in ["APPROVED", "IN_TRANSIT", "COMPLETED", "CANCELLED"]
        },
        "activity": [{"date": d, **v} for d, v in sorted(activity.items())],
        "note": "CONFIRMED ledger totals; DERIVED stock summaries; PREDICTED risk from latest saved assessments; RECOMMENDED proposals. Forecast-based counts cover current complete 14-day forecasts only. Quantities retain medicine units.",
    }
