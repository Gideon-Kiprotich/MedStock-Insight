from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel

from app.models.core import RiskLevel
from app.schemas.common import ORMModel


class RiskGenerateRequest(BaseModel):
    facility_id: UUID
    medicine_id: UUID
    forecast_run_id: UUID | None = None


class RiskAssessmentResponse(ORMModel):
    id: UUID
    facility_id: UUID
    medicine_id: UUID
    forecast_run_id: UUID
    assessed_at: datetime
    risk_level: RiskLevel
    currently_out_of_stock: bool
    days_to_breach: int | None
    projected_breach_date: date | None
    projected_stockout_date: date | None
    projected_shortage_units: Decimal
    inventory_on_hand: Decimal
    safety_stock: Decimal
    reorder_point: Decimal
    incoming_stock_quantity: Decimal
    forecast_horizon_days: int
    calculation_version: str
