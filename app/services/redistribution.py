from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import ROUND_FLOOR, Decimal
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.core import (
    Facility,
    FacilityMedicinePolicy,
    ForecastPoint,
    ForecastRun,
    ForecastRunStatus,
    InventoryBalance,
    Medicine,
    PurchaseOrder,
    PurchaseOrderItem,
    PurchaseOrderStatus,
    RedistributionRecommendation,
    RedistributionRecommendationStatus,
    RiskAssessment,
)

CALCULATION_VERSION = "redistribution-1.0"
DEFAULT_EXPIRY_HOURS = 24


@dataclass(frozen=True)
class FacilityStockPosition:
    facility_id: UUID
    medicine_id: UUID
    current_inventory: Decimal
    safety_stock: Decimal
    forecast_demand: Decimal
    incoming_stock: Decimal
    projected_end_inventory: Decimal
    available_surplus: Decimal
    calculated_shortage: Decimal


def _quantize(value: Decimal) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_FLOOR)


def _forecast_points(
    db: Session,
    facility_id: UUID,
    medicine_id: UUID,
    planning_horizon_days: int,
    forecast_run_id: UUID | None = None,
) -> list[ForecastPoint]:
    if forecast_run_id is not None:
        run = db.get(ForecastRun, forecast_run_id)
        if run is None or run.facility_id != facility_id or run.medicine_id != medicine_id:
            raise HTTPException(status_code=404, detail="Forecast run not found for facility and medicine")
    else:
        run = db.scalar(
            select(ForecastRun)
            .where(
                ForecastRun.facility_id == facility_id,
                ForecastRun.medicine_id == medicine_id,
                ForecastRun.status == ForecastRunStatus.COMPLETED,
            )
            .order_by(ForecastRun.generated_at.desc())
            .limit(1)
        )
    if run is None or run.status != ForecastRunStatus.COMPLETED:
        raise HTTPException(status_code=422, detail="No completed forecast run is available")

    points = db.scalars(
        select(ForecastPoint)
        .where(ForecastPoint.forecast_run_id == run.id)
        .order_by(ForecastPoint.target_date)
        .limit(planning_horizon_days)
    ).all()
    if len(points) < planning_horizon_days:
        raise HTTPException(
            status_code=422,
            detail=f"Forecast contains only {len(points)} daily points; {planning_horizon_days} are required",
        )
    return points


def _current_inventory(db: Session, facility_id: UUID, medicine_id: UUID) -> Decimal:
    balance = db.scalar(
        select(InventoryBalance).where(
            InventoryBalance.facility_id == facility_id,
            InventoryBalance.medicine_id == medicine_id,
        )
    )
    return Decimal(balance.quantity_on_hand) if balance else Decimal("0")


def calculate_stock_position(
    current_inventory: Decimal,
    safety_stock: Decimal,
    forecast_demand: Decimal,
    incoming_stock: Decimal = Decimal("0"),
) -> FacilityStockPosition:
    projected_end = current_inventory + incoming_stock - forecast_demand
    available_surplus = max(projected_end - safety_stock, Decimal("0"))
    calculated_shortage = max(safety_stock - projected_end, Decimal("0"))
    return FacilityStockPosition(
        facility_id=UUID(int=0),
        medicine_id=UUID(int=0),
        current_inventory=_quantize(current_inventory),
        safety_stock=_quantize(safety_stock),
        forecast_demand=_quantize(forecast_demand),
        incoming_stock=_quantize(incoming_stock),
        projected_end_inventory=_quantize(projected_end),
        available_surplus=_quantize(available_surplus),
        calculated_shortage=_quantize(calculated_shortage),
    )


def _confirmed_incoming_stock(db: Session, facility_id: UUID, medicine_id: UUID, start_date: date, end_date: date) -> Decimal:
    rows = db.execute(
        select(
            PurchaseOrder.expected_delivery_date,
            PurchaseOrderItem.quantity_ordered - PurchaseOrderItem.quantity_received,
        )
        .join(PurchaseOrderItem, PurchaseOrderItem.purchase_order_id == PurchaseOrder.id)
        .where(
            PurchaseOrder.facility_id == facility_id,
            PurchaseOrder.status.in_((PurchaseOrderStatus.CONFIRMED, PurchaseOrderStatus.PARTIALLY_RECEIVED)),
            PurchaseOrder.expected_delivery_date >= start_date,
            PurchaseOrder.expected_delivery_date <= end_date,
            PurchaseOrderItem.medicine_id == medicine_id,
            PurchaseOrderItem.quantity_ordered > PurchaseOrderItem.quantity_received,
        )
    ).all()
    return sum(
        (Decimal(quantity) for _, quantity in rows if Decimal(quantity) > 0),
        Decimal("0"),
    )


def _get_position(
    db: Session,
    facility_id: UUID,
    medicine_id: UUID,
    planning_horizon_days: int,
    forecast_run_id: UUID | None,
) -> FacilityStockPosition:
    facility = db.scalar(select(Facility).where(Facility.id == facility_id, Facility.is_active.is_(True)))
    if facility is None:
        raise HTTPException(status_code=404, detail="Facility not found or inactive")
    policy = db.scalar(
        select(FacilityMedicinePolicy).where(
            FacilityMedicinePolicy.facility_id == facility_id,
            FacilityMedicinePolicy.medicine_id == medicine_id,
        )
    )
    if policy is None:
        raise HTTPException(status_code=422, detail="Facility medicine policy is not configured")
    points = _forecast_points(db, facility_id, medicine_id, planning_horizon_days, forecast_run_id)
    forecast_demand = sum((Decimal(point.predicted_demand) for point in points), Decimal("0"))
    current = _current_inventory(db, facility_id, medicine_id)
    incoming = _confirmed_incoming_stock(db, facility_id, medicine_id, points[0].target_date, points[-1].target_date)
    raw = calculate_stock_position(current, Decimal(policy.safety_stock), forecast_demand, incoming_stock=incoming)
    return FacilityStockPosition(
        facility_id=facility_id,
        medicine_id=medicine_id,
        current_inventory=raw.current_inventory,
        safety_stock=raw.safety_stock,
        forecast_demand=raw.forecast_demand,
        incoming_stock=raw.incoming_stock,
        projected_end_inventory=raw.projected_end_inventory,
        available_surplus=raw.available_surplus,
        calculated_shortage=raw.calculated_shortage,
    )


def _latest_risk_assessment(db: Session, facility_id: UUID, medicine_id: UUID) -> RiskAssessment | None:
    return db.scalar(
        select(RiskAssessment)
        .where(
            RiskAssessment.facility_id == facility_id,
            RiskAssessment.medicine_id == medicine_id,
        )
        .order_by(RiskAssessment.assessed_at.desc())
        .limit(1)
    )


def get_surplus_candidates(db: Session, medicine_id: UUID, planning_horizon_days: int) -> list[FacilityStockPosition]:
    facilities = db.scalars(select(Facility).where(Facility.is_active.is_(True)).order_by(Facility.code)).all()
    candidates: list[FacilityStockPosition] = []
    for facility in facilities:
        try:
            position = _get_position(db, facility.id, medicine_id, planning_horizon_days, None)
        except HTTPException:
            continue
        if position.available_surplus > 0:
            candidates.append(position)
    return candidates


def get_shortage_candidates(db: Session, medicine_id: UUID, planning_horizon_days: int) -> list[FacilityStockPosition]:
    facilities = db.scalars(select(Facility).where(Facility.is_active.is_(True)).order_by(Facility.code)).all()
    candidates: list[FacilityStockPosition] = []
    for facility in facilities:
        try:
            position = _get_position(db, facility.id, medicine_id, planning_horizon_days, None)
        except HTTPException:
            continue
        if position.calculated_shortage > 0:
            candidates.append(position)
    return candidates


def generate_recommendation(
    db: Session,
    destination_facility_id: UUID,
    medicine_id: UUID,
    planning_horizon_days: int,
    created_by: UUID,
    source_facility_id: UUID | None = None,
    destination_forecast_run_id: UUID | None = None,
) -> RedistributionRecommendation:
    medicine = db.scalar(select(Medicine).where(Medicine.id == medicine_id, Medicine.is_active.is_(True)))
    destination = db.scalar(
        select(Facility).where(Facility.id == destination_facility_id, Facility.is_active.is_(True))
    )
    if medicine is None:
        raise HTTPException(status_code=404, detail="Medicine not found or inactive")
    if destination is None:
        raise HTTPException(status_code=404, detail="Destination facility not found or inactive")

    destination_position = _get_position(
        db, destination_facility_id, medicine_id, planning_horizon_days, destination_forecast_run_id
    )
    destination_risk = _latest_risk_assessment(db, destination_facility_id, medicine_id)

    if destination_position.calculated_shortage <= 0:
        raise HTTPException(status_code=422, detail="Destination has no calculated shortage for the planning horizon")

    source_ids = [source_facility_id] if source_facility_id else [f.id for f in db.scalars(select(Facility).where(Facility.is_active.is_(True))).all()]
    source_candidates: list[FacilityStockPosition] = []
    for candidate_id in source_ids:
        if candidate_id == destination_facility_id:
            continue
        try:
            position = _get_position(db, candidate_id, medicine_id, planning_horizon_days, None)
        except HTTPException:
            continue
        if position.available_surplus > 0:
            source_candidates.append(position)

    if not source_candidates:
        raise HTTPException(status_code=422, detail="No feasible donor facility with available surplus was found")

    # Deterministic operational choice: donor with the largest feasible surplus.
    source_position = max(source_candidates, key=lambda item: (item.available_surplus, str(item.facility_id)))
    quantity = _quantize(min(source_position.available_surplus, destination_position.calculated_shortage))
    if quantity <= 0:
        raise HTTPException(status_code=422, detail="Calculated recommendation quantity is zero")

    constraints = {
        "same_medicine": True,
        "source_is_active": True,
        "destination_is_active": True,
        "source_has_policy": True,
        "destination_has_policy": True,
        "source_has_forecast": True,
        "destination_has_forecast": True,
        "source_keeps_safety_stock": source_position.projected_end_inventory - quantity >= source_position.safety_stock,
        "quantity_within_destination_need": quantity <= destination_position.calculated_shortage,
        "source_not_destination": source_position.facility_id != destination_facility_id,
    }
    constraints["recommendation_feasible"] = all(constraints.values())
    if not constraints["recommendation_feasible"]:
        raise HTTPException(status_code=422, detail="Redistribution constraints are not satisfied")

    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(hours=DEFAULT_EXPIRY_HOURS)
    recommendation = RedistributionRecommendation(
        source_facility_id=source_position.facility_id,
        destination_facility_id=destination_facility_id,
        medicine_id=medicine_id,
        destination_risk_assessment_id=destination_risk.id if destination_risk else None,
        status=RedistributionRecommendationStatus.PENDING_REVIEW,
        planning_horizon_days=planning_horizon_days,
        source_surplus_units=source_position.available_surplus,
        destination_shortage_units=destination_position.calculated_shortage,
        recommended_quantity=quantity,
        source_inventory_before=source_position.current_inventory,
        destination_inventory_before=destination_position.current_inventory,
        source_safety_stock=source_position.safety_stock,
        destination_safety_stock=destination_position.safety_stock,
        source_projected_end_inventory=source_position.projected_end_inventory,
        destination_projected_end_inventory=destination_position.projected_end_inventory,
        constraint_results=constraints | {"calculation_version": CALCULATION_VERSION},
        expires_at=expires_at,
        created_by=created_by,
    )
    db.add(recommendation)
    db.commit()
    db.refresh(recommendation)
    return recommendation


def decide_recommendation(
    db: Session,
    recommendation_id: UUID,
    approved: bool,
    reviewer_id: UUID,
    note: str | None,
) -> RedistributionRecommendation:
    recommendation = db.get(RedistributionRecommendation, recommendation_id)
    if recommendation is None:
        raise HTTPException(status_code=404, detail="Redistribution recommendation not found")
    if recommendation.status != RedistributionRecommendationStatus.PENDING_REVIEW:
        raise HTTPException(status_code=409, detail=f"Recommendation is already {recommendation.status.value}")
    now = datetime.now(timezone.utc)
    if recommendation.expires_at <= now:
        recommendation.status = RedistributionRecommendationStatus.EXPIRED
        recommendation.reviewed_by = reviewer_id
        recommendation.reviewed_at = now
        recommendation.review_note = "Recommendation expired before decision."
        db.commit()
        raise HTTPException(status_code=409, detail="Redistribution recommendation has expired")

    if approved:
        # Revalidate the critical conditions against current stock and policy before approval.
        source = _current_inventory(db, recommendation.source_facility_id, recommendation.medicine_id)
        destination = _current_inventory(db, recommendation.destination_facility_id, recommendation.medicine_id)
        source_policy = db.scalar(
            select(FacilityMedicinePolicy).where(
                FacilityMedicinePolicy.facility_id == recommendation.source_facility_id,
                FacilityMedicinePolicy.medicine_id == recommendation.medicine_id,
            )
        )
        destination_policy = db.scalar(
            select(FacilityMedicinePolicy).where(
                FacilityMedicinePolicy.facility_id == recommendation.destination_facility_id,
                FacilityMedicinePolicy.medicine_id == recommendation.medicine_id,
            )
        )
        if source_policy is None or destination_policy is None:
            raise HTTPException(status_code=409, detail="Recommendation is stale: policy configuration changed")
        if source - recommendation.recommended_quantity < Decimal(source_policy.safety_stock):
            raise HTTPException(status_code=409, detail="Recommendation is stale: donor would fall below safety stock")
        if destination < 0:
            raise HTTPException(status_code=409, detail="Recommendation is stale: destination inventory is invalid")
        recommendation.constraint_results = {
            **recommendation.constraint_results,
            "approval_source_inventory": str(source),
            "approval_destination_inventory": str(destination),
            "revalidated_at": now.isoformat(),
        }
        recommendation.status = RedistributionRecommendationStatus.APPROVED
    else:
        recommendation.status = RedistributionRecommendationStatus.REJECTED

    recommendation.reviewed_by = reviewer_id
    recommendation.reviewed_at = now
    recommendation.review_note = note
    db.commit()
    db.refresh(recommendation)
    return recommendation
