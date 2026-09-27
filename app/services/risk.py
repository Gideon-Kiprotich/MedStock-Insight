from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
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
    RiskAssessment,
    RiskLevel,
)

CALCULATION_VERSION = "1.0"


@dataclass(frozen=True)
class RiskCalculation:
    risk_level: RiskLevel
    currently_out_of_stock: bool
    days_to_breach: int | None
    projected_breach_date: date | None
    projected_stockout_date: date | None
    projected_shortage_units: Decimal
    incoming_stock_quantity: Decimal
    minimum_projected_stock: Decimal


def classify_risk(days_to_breach: int | None, currently_out_of_stock: bool) -> RiskLevel:
    if currently_out_of_stock or days_to_breach is not None and days_to_breach <= 5:
        return RiskLevel.CRITICAL
    if days_to_breach is not None and days_to_breach <= 10:
        return RiskLevel.HIGH
    if days_to_breach is not None and days_to_breach <= 15:
        return RiskLevel.MEDIUM
    return RiskLevel.LOW


def calculate_risk(
    *,
    assessment_date: date,
    inventory_on_hand: Decimal,
    safety_stock: Decimal,
    forecast_points: list[tuple[date, Decimal]],
    incoming_schedule: list[tuple[date, Decimal]] | None = None,
) -> RiskCalculation:
    incoming_schedule = incoming_schedule or []
    incoming_by_date: dict[date, Decimal] = {}
    for delivery_date, quantity in incoming_schedule:
        incoming_by_date[delivery_date] = incoming_by_date.get(delivery_date, Decimal("0")) + quantity

    currently_out = inventory_on_hand <= 0
    current_breach = inventory_on_hand <= safety_stock
    breach_date: date | None = assessment_date if current_breach else None
    stockout_date: date | None = assessment_date if currently_out else None
    projected = inventory_on_hand
    minimum_projected = inventory_on_hand
    total_incoming = Decimal("0")

    for target_date, demand in forecast_points:
        incoming = incoming_by_date.get(target_date, Decimal("0"))
        total_incoming += incoming
        projected = projected + incoming - demand
        minimum_projected = min(minimum_projected, projected)

        if breach_date is None and projected <= safety_stock:
            breach_date = target_date
        if stockout_date is None and projected <= 0:
            stockout_date = target_date

    if breach_date is None:
        days_to_breach = None
    else:
        days_to_breach = max(0, (breach_date - assessment_date).days)

    projected_shortage = max(Decimal("0"), safety_stock - minimum_projected)
    risk_level = classify_risk(days_to_breach, currently_out)
    return RiskCalculation(
        risk_level=risk_level,
        currently_out_of_stock=currently_out,
        days_to_breach=days_to_breach,
        projected_breach_date=breach_date,
        projected_stockout_date=stockout_date,
        projected_shortage_units=projected_shortage,
        incoming_stock_quantity=total_incoming,
        minimum_projected_stock=minimum_projected,
    )


def _get_forecast_run(
    db: Session, facility_id: UUID, medicine_id: UUID, forecast_run_id: UUID | None
) -> ForecastRun:
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
        if run is None:
            raise HTTPException(status_code=422, detail="No completed forecast run is available")
    if run.status != ForecastRunStatus.COMPLETED:
        raise HTTPException(status_code=422, detail="Selected forecast run is not completed")
    return run


def generate_risk_assessment(
    db: Session, facility_id: UUID, medicine_id: UUID, forecast_run_id: UUID | None = None
) -> RiskAssessment:
    facility = db.scalar(select(Facility).where(Facility.id == facility_id, Facility.is_active.is_(True)))
    medicine = db.scalar(select(Medicine).where(Medicine.id == medicine_id, Medicine.is_active.is_(True)))
    if facility is None:
        raise HTTPException(status_code=404, detail="Facility not found")
    if medicine is None:
        raise HTTPException(status_code=404, detail="Medicine not found")

    policy = db.scalar(
        select(FacilityMedicinePolicy).where(
            FacilityMedicinePolicy.facility_id == facility_id,
            FacilityMedicinePolicy.medicine_id == medicine_id,
        )
    )
    if policy is None:
        raise HTTPException(status_code=422, detail="Facility medicine policy is not configured")

    balance = db.scalar(
        select(InventoryBalance).where(
            InventoryBalance.facility_id == facility_id,
            InventoryBalance.medicine_id == medicine_id,
        )
    )
    inventory_on_hand = Decimal(balance.quantity_on_hand) if balance else Decimal("0")

    run = _get_forecast_run(db, facility_id, medicine_id, forecast_run_id)
    points = db.scalars(
        select(ForecastPoint)
        .where(ForecastPoint.forecast_run_id == run.id)
        .order_by(ForecastPoint.target_date)
    ).all()
    if not points:
        raise HTTPException(status_code=422, detail="Forecast run contains no forecast points")

    end_date = points[-1].target_date
    incoming_rows = db.execute(
        select(PurchaseOrder.expected_delivery_date, (PurchaseOrderItem.quantity_ordered - PurchaseOrderItem.quantity_received))
        .join(PurchaseOrderItem, PurchaseOrderItem.purchase_order_id == PurchaseOrder.id)
        .where(
            PurchaseOrder.facility_id == facility_id,
            PurchaseOrder.status.in_((PurchaseOrderStatus.CONFIRMED, PurchaseOrderStatus.PARTIALLY_RECEIVED)),
            PurchaseOrder.expected_delivery_date >= points[0].target_date,
            PurchaseOrder.expected_delivery_date <= end_date,
            PurchaseOrderItem.medicine_id == medicine_id,
            PurchaseOrderItem.quantity_ordered > PurchaseOrderItem.quantity_received,
        )
    ).all()
    incoming_schedule = [
        (delivery_date, Decimal(quantity))
        for delivery_date, quantity in incoming_rows
        if Decimal(quantity) > 0
    ]

    calculation = calculate_risk(
        assessment_date=date.today(),
        inventory_on_hand=inventory_on_hand,
        safety_stock=Decimal(policy.safety_stock),
        forecast_points=[(point.target_date, Decimal(point.predicted_demand)) for point in points],
        incoming_schedule=incoming_schedule,
    )

    assessment = RiskAssessment(
        facility_id=facility_id,
        medicine_id=medicine_id,
        forecast_run_id=run.id,
        risk_level=calculation.risk_level,
        currently_out_of_stock=calculation.currently_out_of_stock,
        days_to_breach=calculation.days_to_breach,
        projected_breach_date=calculation.projected_breach_date,
        projected_stockout_date=calculation.projected_stockout_date,
        projected_shortage_units=calculation.projected_shortage_units,
        inventory_on_hand=inventory_on_hand,
        safety_stock=Decimal(policy.safety_stock),
        reorder_point=Decimal(policy.reorder_point),
        incoming_stock_quantity=calculation.incoming_stock_quantity,
        forecast_horizon_days=run.horizon_days,
        calculation_version=CALCULATION_VERSION,
    )
    db.add(assessment)
    db.commit()
    db.refresh(assessment)
    return assessment
