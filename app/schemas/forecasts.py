from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.core import ForecastModelCode, ForecastRunStatus
from app.schemas.common import ORMModel


class ForecastGenerateRequest(BaseModel):
    facility_id: UUID
    medicine_id: UUID
    model_code: ForecastModelCode = ForecastModelCode.RANDOM_FOREST
    horizon_days: int = Field(default=30, ge=1, le=90)
    lookback_days: int = Field(default=90, ge=14, le=730)


class ForecastPointResponse(ORMModel):
    id: UUID
    forecast_run_id: UUID
    target_date: date
    predicted_demand: Decimal
    lower_bound: Decimal | None
    upper_bound: Decimal | None


class ForecastRunResponse(ORMModel):
    id: UUID
    facility_id: UUID
    medicine_id: UUID
    model_version_id: UUID
    generated_at: datetime
    forecast_start_date: date
    horizon_days: int
    training_start_date: date
    training_end_date: date
    data_points_used: int
    mae: Decimal | None
    status: ForecastRunStatus
    error_message: str | None


class ForecastSummaryResponse(BaseModel):
    run: ForecastRunResponse
    points: list[ForecastPointResponse]
