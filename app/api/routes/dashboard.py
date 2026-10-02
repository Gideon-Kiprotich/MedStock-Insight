from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.core import (
    RedistributionRecommendationStatus,
    RedistributionTransferStatus,
    RiskLevel,
    User,
)
from app.schemas.dashboard import DashboardResponse
from app.services.dashboard import get_dashboard_read_model

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get(
    "",
    response_model=DashboardResponse,
    summary="Get Operational Dashboard Read Model",
    description=(
        "Returns an aggregated operational dashboard read model summarizing facility stock health, "
        "stockout risk worklist, redistribution queue, transfer activity, and facility metrics."
    ),
)
def get_dashboard(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    facility_id: UUID | None = Query(default=None, description="Filter dashboard metrics by facility ID"),
    medicine_id: UUID | None = Query(default=None, description="Filter dashboard metrics by medicine ID"),
    risk_level: RiskLevel | None = Query(default=None, description="Filter worklist by risk level"),
    transfer_status: RedistributionTransferStatus | None = Query(
        default=None, description="Filter transfer activity by status"
    ),
    recommendation_status: RedistributionRecommendationStatus | None = Query(
        default=None, description="Filter redistribution queue by status"
    ),
) -> DashboardResponse:
    return get_dashboard_read_model(
        db=db,
        facility_id=facility_id,
        medicine_id=medicine_id,
        risk_level=risk_level,
        transfer_status=transfer_status,
        recommendation_status=recommendation_status,
    )
