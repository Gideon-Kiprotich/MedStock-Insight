from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.core import SystemSetting, User
from app.schemas.settings import (
    StockoutThresholds,
    SystemSettingsResponse,
    SystemSettingsUpdate,
)
from app.services.audit import log_audit_event
from app.services.risk import CRITICAL_BREACH_DAYS, HIGH_BREACH_DAYS, MEDIUM_BREACH_DAYS

SETTINGS_ID = UUID("8a767f26-9c2f-4f56-9c43-1a2d4b8d9e10")
TIMEZONE = "Africa/Nairobi"
APPLICATION_VERSION = "0.1.0"
DEFAULT_FORECAST_HORIZON_DAYS = 30
DEFAULT_REPORTING_DAYS = 30


def _response(db: Session, row: SystemSetting | None) -> SystemSettingsResponse:
    updater = db.get(User, row.updated_by) if row and row.updated_by else None
    config = get_settings()
    return SystemSettingsResponse(
        application_name=config.app_name,
        application_version=APPLICATION_VERSION,
        environment=config.environment,
        forecast_default_horizon_days=row.forecast_default_horizon_days
        if row
        else DEFAULT_FORECAST_HORIZON_DAYS,
        reporting_default_days=row.reporting_default_days if row else DEFAULT_REPORTING_DAYS,
        timezone=TIMEZONE,
        stockout_thresholds=StockoutThresholds(
            critical_days=CRITICAL_BREACH_DAYS,
            high_days=HIGH_BREACH_DAYS,
            medium_days=MEDIUM_BREACH_DAYS,
            out_of_stock_is_critical=True,
        ),
        updated_at=row.updated_at if row else None,
        updated_by=row.updated_by if row else None,
        updated_by_name=updater.full_name if updater else None,
    )


def get_system_settings(db: Session) -> SystemSettingsResponse:
    return _response(db, db.get(SystemSetting, SETTINGS_ID))


def get_forecast_default_horizon(db: Session) -> int:
    row = db.get(SystemSetting, SETTINGS_ID)
    return row.forecast_default_horizon_days if row else DEFAULT_FORECAST_HORIZON_DAYS


def update_system_settings(
    db: Session,
    payload: SystemSettingsUpdate,
    current_user: User,
) -> SystemSettingsResponse:
    row = db.get(SystemSetting, SETTINGS_ID)
    previous = (
        {
            "forecast_default_horizon_days": row.forecast_default_horizon_days,
            "reporting_default_days": row.reporting_default_days,
        }
        if row
        else None
    )
    if row is None:
        row = SystemSetting(id=SETTINGS_ID)
        db.add(row)
    row.forecast_default_horizon_days = payload.forecast_default_horizon_days
    row.reporting_default_days = payload.reporting_default_days
    row.updated_by = current_user.id
    db.flush()
    log_audit_event(
        db=db,
        user_id=current_user.id,
        action="SYSTEM_SETTINGS_UPDATED",
        entity_type="system_settings",
        entity_id=row.id,
        previous_state=previous,
        new_state={
            "forecast_default_horizon_days": row.forecast_default_horizon_days,
            "reporting_default_days": row.reporting_default_days,
        },
    )
    db.commit()
    db.refresh(row)
    return _response(db, row)
