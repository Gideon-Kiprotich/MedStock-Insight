from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.core import ForecastPoint, ForecastRun, RoleCode, User
from app.schemas.common import CollectionResponse, Pagination
from app.schemas.forecasts import (
    ForecastGenerateRequest,
    ForecastPointResponse,
    ForecastRunResponse,
    ForecastSummaryResponse,
)
from app.services.forecasting import generate_forecast

router = APIRouter(prefix="/forecasts", tags=["Forecasts"])


@router.post("/generate", response_model=ForecastSummaryResponse, status_code=status.HTTP_201_CREATED)
def create_forecast(
    payload: ForecastGenerateRequest,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(RoleCode.ADMINISTRATOR, RoleCode.SUPPLY_CHAIN_MANAGER))],
) -> ForecastSummaryResponse:
    run = generate_forecast(
        db=db,
        facility_id=payload.facility_id,
        medicine_id=payload.medicine_id,
        model_code=payload.model_code,
        horizon_days=payload.horizon_days,
        lookback_days=payload.lookback_days,
    )
    points = db.scalars(
        select(ForecastPoint).where(ForecastPoint.forecast_run_id == run.id).order_by(ForecastPoint.target_date)
    ).all()
    return ForecastSummaryResponse(
        run=ForecastRunResponse.model_validate(run),
        points=[ForecastPointResponse.model_validate(point) for point in points],
    )


@router.get("", response_model=CollectionResponse[ForecastRunResponse])
def list_forecasts(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
    facility_id: UUID | None = Query(default=None),
    medicine_id: UUID | None = Query(default=None),
    page: int = 1,
    page_size: int = 50,
) -> CollectionResponse[ForecastRunResponse]:
    filters = []
    if facility_id:
        filters.append(ForecastRun.facility_id == facility_id)
    if medicine_id:
        filters.append(ForecastRun.medicine_id == medicine_id)

    page = max(page, 1)
    page_size = min(max(page_size, 1), 200)
    query = select(ForecastRun).where(*filters).order_by(ForecastRun.generated_at.desc())
    items = db.scalars(query.offset((page - 1) * page_size).limit(page_size)).all()
    total = db.scalar(select(func.count()).select_from(ForecastRun).where(*filters)) or 0
    return CollectionResponse(
        data=[ForecastRunResponse.model_validate(item) for item in items],
        pagination=Pagination(
            page=page,
            page_size=page_size,
            total=total,
            total_pages=(total + page_size - 1) // page_size,
        ),
    )


@router.get("/{run_id}", response_model=ForecastSummaryResponse)
def get_forecast(
    run_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
) -> ForecastSummaryResponse:
    run = db.get(ForecastRun, run_id)
    if run is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Forecast run not found")
    points = db.scalars(
        select(ForecastPoint).where(ForecastPoint.forecast_run_id == run.id).order_by(ForecastPoint.target_date)
    ).all()
    return ForecastSummaryResponse(
        run=ForecastRunResponse.model_validate(run),
        points=[ForecastPointResponse.model_validate(point) for point in points],
    )
