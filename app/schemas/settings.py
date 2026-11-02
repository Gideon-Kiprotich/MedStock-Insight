from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

ForecastHorizon = Literal[7, 14, 30]
ReportingPeriod = Literal[7, 30, 90]


class StockoutThresholds(BaseModel):
    critical_days: int
    high_days: int
    medium_days: int
    out_of_stock_is_critical: bool


class SystemSettingsResponse(BaseModel):
    application_name: str
    application_version: str
    environment: str
    forecast_default_horizon_days: ForecastHorizon
    reporting_default_days: ReportingPeriod
    timezone: str
    stockout_thresholds: StockoutThresholds
    updated_at: datetime | None
    updated_by: UUID | None
    updated_by_name: str | None


class SystemSettingsUpdate(BaseModel):
    forecast_default_horizon_days: ForecastHorizon
    reporting_default_days: ReportingPeriod
