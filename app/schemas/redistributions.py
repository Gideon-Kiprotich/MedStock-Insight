from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.core import RedistributionRecommendationStatus
from app.schemas.common import ORMModel


class RedistributionGenerateRequest(BaseModel):
    destination_facility_id: UUID
    medicine_id: UUID
    planning_horizon_days: int = Field(default=14, ge=1, le=90)
    source_facility_id: UUID | None = None
    forecast_run_id: UUID | None = None


class RedistributionDecisionRequest(BaseModel):
    note: str | None = Field(default=None, max_length=1000)


class ConstraintResults(BaseModel):
    same_medicine: bool
    source_is_active: bool
    destination_is_active: bool
    source_has_policy: bool
    destination_has_policy: bool
    source_has_forecast: bool
    destination_has_forecast: bool
    source_keeps_safety_stock: bool
    quantity_within_destination_need: bool
    source_not_destination: bool
    recommendation_feasible: bool


class RedistributionRecommendationResponse(ORMModel):
    id: UUID
    source_facility_id: UUID
    destination_facility_id: UUID
    medicine_id: UUID
    destination_risk_assessment_id: UUID | None
    status: RedistributionRecommendationStatus
    planning_horizon_days: int
    source_surplus_units: Decimal
    destination_shortage_units: Decimal
    recommended_quantity: Decimal
    source_inventory_before: Decimal
    destination_inventory_before: Decimal
    source_safety_stock: Decimal
    destination_safety_stock: Decimal
    source_projected_end_inventory: Decimal
    destination_projected_end_inventory: Decimal
    constraint_results: dict
    expires_at: datetime
    created_by: UUID
    reviewed_by: UUID | None
    reviewed_at: datetime | None
    review_note: str | None
    created_at: datetime
    updated_at: datetime


class RedistributionCandidateResponse(BaseModel):
    facility_id: UUID
    medicine_id: UUID
    current_inventory: Decimal
    safety_stock: Decimal
    forecast_demand: Decimal
    incoming_stock: Decimal = Decimal("0")
    available_surplus: Decimal = Decimal("0")
    calculated_shortage: Decimal = Decimal("0")
    risk_level: str | None = None
