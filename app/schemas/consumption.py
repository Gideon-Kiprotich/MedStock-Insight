from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

from app.schemas.common import Pagination

ConsumptionSortField = Literal[
    "transaction_date",
    "quantity",
    "facility_name",
    "medicine_name",
    "created_at",
]
ConsumptionSortOrder = Literal["asc", "desc"]


class ConsumptionEntryResponse(BaseModel):
    id: UUID
    facility_id: UUID
    facility_name: str
    medicine_id: UUID
    medicine_name: str
    unit_of_measure: str
    quantity: float
    transaction_date: date
    reference_number: str | None
    notes: str | None
    recorded_by: UUID
    recorded_by_name: str
    created_at: datetime


class ConsumptionSummaryResponse(BaseModel):
    total_quantity: float
    transaction_count: int
    distinct_medicines: int
    days_covered: int
    daily_average: float
    first_date: date | None
    last_date: date | None


class ConsumptionTrendPointResponse(BaseModel):
    date: date
    quantity: float
    transaction_count: int


class ConsumptionResponse(BaseModel):
    data: list[ConsumptionEntryResponse]
    pagination: Pagination
    summary: ConsumptionSummaryResponse
    trend: list[ConsumptionTrendPointResponse]
