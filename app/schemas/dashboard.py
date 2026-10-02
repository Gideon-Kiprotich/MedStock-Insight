from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.core import (
    RedistributionRecommendationStatus,
    RedistributionTransferStatus,
    RiskLevel,
)
from app.schemas.common import ORMModel


class DashboardInventoryHealth(BaseModel):
    healthy_count: int = Field(default=0, ge=0)
    at_risk_count: int = Field(default=0, ge=0)
    stockout_count: int = Field(default=0, ge=0)


class DashboardSummary(BaseModel):
    facilities_count: int = Field(default=0, ge=0)
    medicines_tracked: int = Field(default=0, ge=0)
    active_stockouts: int = Field(default=0, ge=0)
    critical_risk_count: int = Field(default=0, ge=0)
    high_risk_count: int = Field(default=0, ge=0)
    medium_risk_count: int = Field(default=0, ge=0)
    low_risk_count: int = Field(default=0, ge=0)
    pending_redistribution_count: int = Field(default=0, ge=0)
    in_transit_transfer_count: int = Field(default=0, ge=0)
    inventory_health: DashboardInventoryHealth
    data_timestamp: datetime


class DashboardRiskItem(BaseModel):
    facility_id: UUID
    facility_code: str
    facility_name: str
    medicine_id: UUID
    medicine_code: str
    generic_name: str
    current_stock: Decimal
    safety_stock: Decimal
    days_until_breach: int | None
    projected_stockout_date: date | None
    risk_level: RiskLevel
    forecast_run_id: UUID | None
    assessed_at: datetime
    data_classification: str = "PREDICTED"


class DashboardRedistributionItem(BaseModel):
    recommendation_id: UUID
    source_facility_id: UUID
    source_facility_name: str
    destination_facility_id: UUID
    destination_facility_name: str
    medicine_id: UUID
    medicine_name: str
    recommended_quantity: Decimal
    source_surplus_units: Decimal
    destination_shortage_units: Decimal
    status: RedistributionRecommendationStatus
    created_at: datetime
    expires_at: datetime
    data_classification: str = "RECOMMENDED"


class DashboardTransferItem(BaseModel):
    transfer_id: UUID
    recommendation_id: UUID
    source_facility_id: UUID
    source_facility_name: str
    destination_facility_id: UUID
    destination_facility_name: str
    medicine_id: UUID
    medicine_name: str
    quantity: Decimal
    status: RedistributionTransferStatus
    created_at: datetime
    dispatched_at: datetime | None
    received_at: datetime | None
    data_classification: str = "CONFIRMED"


class DashboardFacilitySummary(BaseModel):
    facility_id: UUID
    facility_code: str
    facility_name: str
    tracked_medicines: int = Field(default=0, ge=0)
    active_stockouts: int = Field(default=0, ge=0)
    critical_high_risk_count: int = Field(default=0, ge=0)
    pending_redistributions: int = Field(default=0, ge=0)
    in_transit_transfers: int = Field(default=0, ge=0)
    healthy_count: int = Field(default=0, ge=0)
    at_risk_count: int = Field(default=0, ge=0)
    stockout_count: int = Field(default=0, ge=0)


class DashboardResponse(BaseModel):
    summary: DashboardSummary
    risk_worklist: list[DashboardRiskItem]
    redistribution_queue: list[DashboardRedistributionItem]
    recent_transfers: list[DashboardTransferItem]
    facility_summaries: list[DashboardFacilitySummary]
