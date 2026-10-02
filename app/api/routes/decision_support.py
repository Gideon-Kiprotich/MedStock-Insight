"""Read-only evaluation and explanation views over recorded decision-support data."""
from datetime import date, timedelta
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.core import (
    Facility,
    ForecastModelCode,
    ForecastPoint,
    ForecastRun,
    InventoryTransaction,
    InventoryTransactionType,
    Medicine,
    MLModelVersion,
    RedistributionRecommendation,
    RedistributionRecommendationStatus,
    RiskAssessment,
    User,
)
from app.services.forecasting import (
    FEATURE_NAMES,
    HOLDOUT_DAYS,
    MIN_TRAIN_DAYS,
    build_daily_consumption,
    evaluate_series,
)
from app.services.redistribution import get_surplus_candidates

router = APIRouter(tags=["Decision Support"])


@router.get("/forecast-evaluation")
def forecast_evaluation(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
    facility_id: UUID | None = None,
    medicine_id: UUID | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    end = end_date or date.today()
    start = start_date or end - timedelta(days=89)
    if end < start or (end - start).days > 730:
        raise HTTPException(status_code=422, detail="Evaluation date range must be 1–731 days")
    filters = [InventoryTransaction.transaction_type == InventoryTransactionType.CONSUMPTION,
               InventoryTransaction.transaction_date >= start,
               InventoryTransaction.transaction_date <= end]
    if facility_id:
        filters.append(InventoryTransaction.facility_id == facility_id)
    if medicine_id:
        filters.append(InventoryTransaction.medicine_id == medicine_id)
    pairs = db.execute(
        select(InventoryTransaction.facility_id, InventoryTransaction.medicine_id,
               func.min(InventoryTransaction.transaction_date),
               func.max(InventoryTransaction.transaction_date))
        .where(*filters)
        .group_by(InventoryTransaction.facility_id, InventoryTransaction.medicine_id)
        .order_by(InventoryTransaction.facility_id, InventoryTransaction.medicine_id)
        .offset(offset).limit(limit)
    ).all()
    rows = []
    evaluated_series = 0
    for pair_facility, pair_medicine, first, last in pairs:
        facility = db.get(Facility, pair_facility)
        medicine = db.get(Medicine, pair_medicine)
        # A missing leading/trailing interval is unknown, not observed zero demand.
        series_start = max(start, first)
        series_end = min(end, last)
        daily = build_daily_consumption(db, pair_facility, pair_medicine, series_start, series_end)
        values = [amount for _, amount in daily]
        measured = False
        for model in (ForecastModelCode.MOVING_AVERAGE_7D, ForecastModelCode.RANDOM_FOREST):
            result = evaluate_series(values, model, series_start)
            if result:
                measured = True
            rows.append({
                "facility_id": pair_facility, "medicine_id": pair_medicine,
                "facility_name": facility.name if facility else None,
                "medicine_name": medicine.generic_name if medicine else None,
                "model": model, "training_start": series_start,
                "training_end": series_end - timedelta(days=HOLDOUT_DAYS) if result else None,
                "holdout_start": series_end - timedelta(days=HOLDOUT_DAYS - 1) if result else None,
                "holdout_end": series_end if result else None,
                "training_observations": result.training_observations if result else None,
                "observations": result.observations if result else 0,
                "mae": round(result.mae, 4) if result else None,
                "rmse": round(result.rmse, 4) if result else None,
                "wape": round(result.wape, 2) if result and result.wape is not None else None,
                "status": "MEASURED" if result else "INSUFFICIENT_DATA",
                "reason": None if result else (
                    f"Requires at least {MIN_TRAIN_DAYS} training and {HOLDOUT_DAYS} holdout days, "
                    "14 nonzero training days and 2 nonzero holdout days."
                ),
            })
        evaluated_series += int(measured)
    return {
        "start_date": start, "end_date": end, "evaluated_series": evaluated_series, "offset": offset, "limit": limit,
        "methodology": "Fixed final 14-day temporal holdout; one-step predictions use only earlier actual demand. "
                       "Random Forest is fitted on training data only. WAPE is omitted when actual demand sums to zero.",
        "data_note": "Evaluation reflects recorded consumption, which is synthetic in the demonstration environment; "
                     "it does not establish future or clinical accuracy.",
        "results": rows,
    }


@router.get("/forecasts/{run_id}/explanation")
def forecast_explanation(
    run_id: UUID, db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
):
    run = db.get(ForecastRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Forecast run not found")
    version = db.get(MLModelVersion, run.model_version_id)
    model = version.code if version else None
    features = (
        [{"name": name, "description": description} for name, description in zip(FEATURE_NAMES, (
            "Prior day's recorded consumption", "Consumption seven days earlier",
            "Mean of the preceding seven days", "Mean of the preceding 28 days",
            "Calendar weekday of the target date (Monday=0)",
        ))] if model == ForecastModelCode.RANDOM_FOREST else
        [{"name": "rolling_mean_7d", "description": "Mean of the preceding seven days"}]
    )
    return {
        "forecast_run_id": run.id, "model": model,
        "model_version": version.version if version else None,
        "training_start": run.training_start_date, "training_end": run.training_end_date,
        "training_observations": run.data_points_used,
        "forecast_start": run.forecast_start_date, "horizon_days": run.horizon_days,
        "features": features,
        "feature_importance": None,
        "note": "Feature definitions describe the implemented model. Per-run feature values and importance "
                "were not persisted, so no importance score is asserted. Older run MAE may use a different holdout; "
                "use Forecast Evaluation for comparable holdout results.",
    }


@router.get("/risk-assessments/{assessment_id}/explanation")
def risk_explanation(
    assessment_id: UUID, db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
):
    assessment = db.get(RiskAssessment, assessment_id)
    if assessment is None:
        raise HTTPException(status_code=404, detail="Risk assessment not found")
    points = db.scalars(select(ForecastPoint).where(
        ForecastPoint.forecast_run_id == assessment.forecast_run_id
    ).order_by(ForecastPoint.target_date)).all()
    forecast_demand = sum((point.predicted_demand for point in points), 0)
    projected_end = assessment.inventory_on_hand + assessment.incoming_stock_quantity - forecast_demand
    recommendations = db.scalars(select(RedistributionRecommendation).where(
        RedistributionRecommendation.destination_risk_assessment_id == assessment.id
    ).order_by(RedistributionRecommendation.created_at.desc())).all()
    pending = next((rec for rec in recommendations if
                    rec.status == RedistributionRecommendationStatus.PENDING_REVIEW), None)
    donor = None
    if assessment.projected_shortage_units > 0 and points:
        candidates = [candidate for candidate in get_surplus_candidates(
            db, assessment.medicine_id, min(len(points), 14)
        ) if candidate.facility_id != assessment.facility_id]
        if candidates:
            donor = max(candidates, key=lambda item: (item.available_surplus, str(item.facility_id)))
    return {
        "assessment_id": assessment.id, "assessed_at": assessment.assessed_at,
        "facility_id": assessment.facility_id, "medicine_id": assessment.medicine_id,
        "current_stock": assessment.inventory_on_hand, "safety_stock": assessment.safety_stock,
        "forecasted_demand": forecast_demand, "forecast_days": len(points),
        "projected_inventory": projected_end,
        "days_to_breach": assessment.days_to_breach,
        "projected_breach_date": assessment.projected_breach_date,
        "projected_stockout_date": assessment.projected_stockout_date,
        "risk_level": assessment.risk_level,
        "confirmed_incoming_quantity": assessment.incoming_stock_quantity,
        "projected_shortage": assessment.projected_shortage_units,
        "feasible_donor_facility_id": donor.facility_id if donor else None,
        "feasible_donor_surplus": donor.available_surplus if donor else None,
        "recommendation_id": pending.id if pending else None,
        "recommended_quantity": pending.recommended_quantity if pending else None,
        "human_action": "An Administrator or Supply Chain Manager must review and approve a recommendation; "
                        "a physical transfer requires separate execution.",
        "note": "Risk and demand reflect the saved assessment/forecast. Donor availability is read from "
                "current positions and must be revalidated before approval.",
    }


@router.get("/redistributions/recommendations/{recommendation_id}/explanation")
def recommendation_explanation(
    recommendation_id: UUID, db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
):
    rec = db.get(RedistributionRecommendation, recommendation_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="Redistribution recommendation not found")
    source, destination, medicine = (
        db.get(Facility, rec.source_facility_id),
        db.get(Facility, rec.destination_facility_id),
        db.get(Medicine, rec.medicine_id),
    )
    return {
        "recommendation_id": rec.id, "source_facility": source.name if source else str(rec.source_facility_id),
        "destination_facility": destination.name if destination else str(rec.destination_facility_id),
        "medicine": medicine.generic_name if medicine else str(rec.medicine_id),
        "source_current_stock": rec.source_inventory_before,
        "source_usable_surplus": rec.source_surplus_units,
        "destination_current_stock": rec.destination_inventory_before,
        "destination_projected_shortage": rec.destination_shortage_units,
        "source_safety_stock": rec.source_safety_stock,
        "destination_safety_stock": rec.destination_safety_stock,
        "source_projected_after_transfer": rec.source_projected_end_inventory - rec.recommended_quantity,
        "recommended_quantity": rec.recommended_quantity,
        "status": rec.status,
        "reason": "Destination has a projected shortage; the source had usable surplus in the planning "
                  "horizon and its projected stock remains above safety stock after this proposed transfer.",
        "note": "Values are the saved recommendation snapshot. Approval revalidates current stock. "
                "This recommendation does not execute a transfer.",
    }
