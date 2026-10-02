"""Isolated, replayable experiments using existing stock and risk calculations."""

import hashlib
import json
from datetime import date, timedelta, timezone
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.core import (
    AnalyticalExperiment,
    Facility,
    FacilityMedicinePolicy,
    ForecastRun,
    InventoryBalance,
    Medicine,
    PurchaseOrder,
    PurchaseOrderItem,
    PurchaseOrderStatus,
)
from app.services.redistribution import _forecast_points, calculate_stock_position
from app.services.risk import calculate_risk

VERSION = "scenario-1.0"


class ScenarioParameters(BaseModel):
    facility_id: UUID
    medicine_id: UUID
    demand_adjustment_pct: int = Field(default=0, ge=-30, le=100)
    inventory_adjustment_pct: int = Field(default=0, ge=-90, le=100)
    lead_time_adjustment_days: int = Field(default=0, ge=0, le=30)
    horizon_days: int = Field(default=14, ge=1, le=90)


def capture_position(
    db: Session, facility: Facility, medicine_id: UUID, horizon: int, today: date
) -> dict:
    policy = db.scalar(
        select(FacilityMedicinePolicy).where(
            FacilityMedicinePolicy.facility_id == facility.id,
            FacilityMedicinePolicy.medicine_id == medicine_id,
        )
    )
    if not policy:
        raise HTTPException(422, "No facility medicine policy is configured")
    points = _forecast_points(db, facility.id, medicine_id, horizon)
    if [p.target_date for p in points] != [today + timedelta(days=i + 1) for i in range(horizon)]:
        raise HTTPException(
            422, "Forecast is stale or incomplete. Generate a current forecast first."
        )
    balance = db.scalar(
        select(InventoryBalance).where(
            InventoryBalance.facility_id == facility.id, InventoryBalance.medicine_id == medicine_id
        )
    )
    incoming = db.execute(
        select(
            PurchaseOrder.expected_delivery_date,
            PurchaseOrderItem.quantity_ordered - PurchaseOrderItem.quantity_received,
        )
        .join(PurchaseOrderItem)
        .where(
            PurchaseOrder.facility_id == facility.id,
            PurchaseOrderItem.medicine_id == medicine_id,
            PurchaseOrder.status.in_(
                [PurchaseOrderStatus.CONFIRMED, PurchaseOrderStatus.PARTIALLY_RECEIVED]
            ),
            PurchaseOrder.expected_delivery_date >= points[0].target_date,
            PurchaseOrder.expected_delivery_date <= points[-1].target_date,
            PurchaseOrderItem.quantity_ordered > PurchaseOrderItem.quantity_received,
        )
    ).all()
    run = db.get(ForecastRun, points[0].forecast_run_id)
    return {
        "facility_id": str(facility.id),
        "facility_name": facility.name,
        "transfer_eligible": facility.transfer_eligible,
        "stock": str(balance.quantity_on_hand if balance else 0),
        "safety": str(policy.safety_stock),
        "forecast_run_id": str(run.id),
        "model_version_id": str(run.model_version_id),
        "points": [[p.target_date.isoformat(), str(p.predicted_demand)] for p in points],
        "incoming": [[d.isoformat(), str(q)] for d, q in incoming],
    }


def position_result(
    snapshot: dict, today: date, demand_pct: int = 0, inventory_pct: int = 0, delay: int = 0
) -> dict:
    stock = Decimal(snapshot["stock"]) * (1 + Decimal(inventory_pct) / 100)
    safety = Decimal(snapshot["safety"])
    points = [
        (date.fromisoformat(d), Decimal(q) * (1 + Decimal(demand_pct) / 100))
        for d, q in snapshot["points"]
    ]
    incoming = [
        (date.fromisoformat(d) + timedelta(days=delay), Decimal(q)) for d, q in snapshot["incoming"]
    ]
    risk = calculate_risk(
        assessment_date=today,
        inventory_on_hand=stock,
        safety_stock=safety,
        forecast_points=points,
        incoming_schedule=incoming,
    )
    demand = sum((q for _, q in points), Decimal(0))
    position = calculate_stock_position(stock, safety, demand, risk.incoming_stock_quantity)
    projected = stock
    trajectory = []
    for d, q in points:
        projected += sum((v for day, v in incoming if day == d), Decimal(0)) - q
        trajectory.append({"date": d, "projected_stock": projected, "daily_demand": q})
    return {
        "daily_demand": demand / len(points),
        "current_stock": stock,
        "days_to_breach": risk.days_to_breach,
        "risk_level": risk.risk_level.value,
        "projected_shortage": risk.projected_shortage_units,
        "end_shortage": position.calculated_shortage,
        "projected_end_inventory": position.projected_end_inventory,
        "incoming_quantity": risk.incoming_stock_quantity,
        "projected_stockout_date": risk.projected_stockout_date,
        "available_surplus": max(Decimal(0), min(position.available_surplus, stock - safety)),
        "trajectory": trajectory,
    }


def simulate(context: dict, params: dict) -> dict:
    if context["version"] != VERSION:
        raise HTTPException(409, "Saved calculation version is unsupported by this service")
    today = date.fromisoformat(context["assessment_date"])
    donor_positions = [(d, position_result(d, today)) for d in context["donors"]]

    def outcome(demand=0, inventory=0, delay=0):
        result = position_result(context["destination"], today, demand, inventory, delay)
        donors = [(d, p) for d, p in donor_positions if p["available_surplus"] > 0]
        donor = (
            max(donors, key=lambda item: (item[1]["available_surplus"], item[0]["facility_id"]))
            if donors
            else None
        )
        feasible = bool(
            context["destination"]["transfer_eligible"] and donor and result["end_shortage"] > 0
        )
        result.update(
            {
                "feasible_donor": donor[0]["facility_name"] if feasible else None,
                "feasible_donor_id": donor[0]["facility_id"] if feasible else None,
                "recommended_quantity": min(result["end_shortage"], donor[1]["available_surplus"])
                if feasible
                else Decimal(0),
                "redistribution_feasible": feasible,
            }
        )
        return result

    baseline = outcome()
    scenario = outcome(
        params["demand_adjustment_pct"],
        params["inventory_adjustment_pct"],
        params["lead_time_adjustment_days"],
    )
    differences = {
        key: scenario[key] - baseline[key]
        for key in [
            "daily_demand",
            "current_stock",
            "projected_shortage",
            "recommended_quantity",
            "incoming_quantity",
        ]
    }
    differences["days_to_breach"] = (
        scenario["days_to_breach"] - baseline["days_to_breach"]
        if baseline["days_to_breach"] is not None and scenario["days_to_breach"] is not None
        else None
    )
    differences["risk_level"] = baseline["risk_level"] + " → " + scenario["risk_level"]
    differences["feasible_donor"] = (
        "Unchanged" if baseline["feasible_donor"] == scenario["feasible_donor"] else "Changed"
    )
    reasons = [
        f"Daily projected consumption changes from {baseline['daily_demand']:.2f} to {scenario['daily_demand']:.2f}; opening stock from {baseline['current_stock']:.2f} to {scenario['current_stock']:.2f}.",
        f"Confirmed incoming stock within the horizon changes from {baseline['incoming_quantity']:.2f} to {scenario['incoming_quantity']:.2f} after a {params['lead_time_adjustment_days']}-day delivery delay.",
        f"Safety-stock breach: {baseline['days_to_breach']} → {scenario['days_to_breach']} days (None means no breach in this horizon). Risk: {baseline['risk_level']} → {scenario['risk_level']}.",
        "Donors remain at baseline. Usable donor surplus is capped by both projected surplus and current stock above safety. The suggested quantity addresses end-of-horizon shortage; it does not guarantee prevention of an earlier stockout or execute a transfer.",
    ]
    return jsonable_encoder(
        {
            "label": "SIMULATION — NOT LIVE INVENTORY",
            "baseline": baseline,
            "scenario": scenario,
            "differences": differences,
            "explanations": reasons,
        }
    )


def save_experiment(
    db: Session, kind: str, params: dict, context: dict, result: dict, user_id: UUID | None = None
) -> AnalyticalExperiment:
    context = jsonable_encoder(context)
    params = jsonable_encoder(params)
    fingerprint = hashlib.sha256(
        json.dumps({"parameters": params, "context": context}, sort_keys=True).encode()
    ).hexdigest()
    record = AnalyticalExperiment(
        kind=kind,
        parameters=params,
        context=context,
        result=jsonable_encoder(result),
        fingerprint=fingerprint,
        created_by=user_id,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def serialize(record: AnalyticalExperiment) -> dict:
    return {
        "id": record.id,
        "created_at": record.created_at.replace(tzinfo=timezone.utc)
        if record.created_at.tzinfo is None
        else record.created_at,
        "fingerprint": record.fingerprint,
        "parameters": record.parameters,
        "context": record.context,
        **record.result,
    }


def create_scenario(db: Session, params: ScenarioParameters, user_id: UUID | None = None) -> dict:
    facility = db.get(Facility, params.facility_id)
    medicine = db.get(Medicine, params.medicine_id)
    if not facility or not facility.is_active or not medicine or not medicine.is_active:
        raise HTTPException(404, "Active facility and medicine are required")
    today = date.today()
    destination = capture_position(db, facility, medicine.id, params.horizon_days, today)
    donors, excluded = [], []
    for donor in db.scalars(
        select(Facility)
        .where(
            Facility.is_active.is_(True),
            Facility.transfer_eligible.is_(True),
            Facility.id != facility.id,
        )
        .order_by(Facility.code)
    ).all():
        try:
            donors.append(capture_position(db, donor, medicine.id, params.horizon_days, today))
        except HTTPException as exc:
            excluded.append({"facility": donor.name, "reason": exc.detail})
    context = {
        "version": VERSION,
        "assessment_date": today.isoformat(),
        "destination": destination,
        "medicine_name": f"{medicine.generic_name} {medicine.strength or ''} {medicine.dosage_form or ''}",
        "donors": donors,
        "excluded_donors": excluded,
    }
    data = params.model_dump(mode="json")
    return serialize(
        save_experiment(db, "SCENARIO", data, context, simulate(context, data), user_id)
    )
