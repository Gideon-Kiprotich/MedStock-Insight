from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.core import (
    RedistributionRecommendation,
    RedistributionRecommendationStatus,
    RoleCode,
    User,
)
from app.schemas.common import CollectionResponse, Pagination
from app.schemas.redistributions import (
    RedistributionCandidateResponse,
    RedistributionDecisionRequest,
    RedistributionGenerateRequest,
    RedistributionRecommendationResponse,
)
from app.services.redistribution import (
    decide_recommendation,
    generate_recommendation,
    get_shortage_candidates,
    get_surplus_candidates,
)

router = APIRouter(prefix="/redistributions", tags=["Redistributions"])


@router.post("/recommendations/generate", response_model=RedistributionRecommendationResponse, status_code=status.HTTP_201_CREATED)
def create_recommendation(
    payload: RedistributionGenerateRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleCode.ADMINISTRATOR, RoleCode.SUPPLY_CHAIN_MANAGER))],
) -> RedistributionRecommendationResponse:
    recommendation = generate_recommendation(
        db=db,
        destination_facility_id=payload.destination_facility_id,
        medicine_id=payload.medicine_id,
        planning_horizon_days=payload.planning_horizon_days,
        created_by=current_user.id,
        source_facility_id=payload.source_facility_id,
        destination_forecast_run_id=payload.forecast_run_id,
    )
    return RedistributionRecommendationResponse.model_validate(recommendation)


@router.get("/recommendations", response_model=CollectionResponse[RedistributionRecommendationResponse])
def list_recommendations(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
    status_filter: RedistributionRecommendationStatus | None = Query(default=None, alias="status"),
    destination_facility_id: UUID | None = None,
    source_facility_id: UUID | None = None,
    medicine_id: UUID | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
) -> CollectionResponse[RedistributionRecommendationResponse]:
    filters = []
    if status_filter:
        filters.append(RedistributionRecommendation.status == status_filter)
    if destination_facility_id:
        filters.append(RedistributionRecommendation.destination_facility_id == destination_facility_id)
    if source_facility_id:
        filters.append(RedistributionRecommendation.source_facility_id == source_facility_id)
    if medicine_id:
        filters.append(RedistributionRecommendation.medicine_id == medicine_id)

    query = select(RedistributionRecommendation).where(*filters).order_by(RedistributionRecommendation.created_at.desc())
    items = db.scalars(query.offset((page - 1) * page_size).limit(page_size)).all()
    total = db.scalar(select(func.count()).select_from(RedistributionRecommendation).where(*filters)) or 0
    return CollectionResponse(
        data=[RedistributionRecommendationResponse.model_validate(item) for item in items],
        pagination=Pagination(
            page=page,
            page_size=page_size,
            total=total,
            total_pages=(total + page_size - 1) // page_size,
        ),
    )


@router.get("/recommendations/{recommendation_id}", response_model=RedistributionRecommendationResponse)
def get_recommendation(
    recommendation_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
) -> RedistributionRecommendationResponse:
    recommendation = db.get(RedistributionRecommendation, recommendation_id)
    if recommendation is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Redistribution recommendation not found")
    return RedistributionRecommendationResponse.model_validate(recommendation)


@router.post("/recommendations/{recommendation_id}/approve", response_model=RedistributionRecommendationResponse)
def approve_recommendation(
    recommendation_id: UUID,
    payload: RedistributionDecisionRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleCode.ADMINISTRATOR, RoleCode.SUPPLY_CHAIN_MANAGER))],
) -> RedistributionRecommendationResponse:
    recommendation = decide_recommendation(db, recommendation_id, True, current_user.id, payload.note)
    return RedistributionRecommendationResponse.model_validate(recommendation)


@router.post("/recommendations/{recommendation_id}/reject", response_model=RedistributionRecommendationResponse)
def reject_recommendation(
    recommendation_id: UUID,
    payload: RedistributionDecisionRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleCode.ADMINISTRATOR, RoleCode.SUPPLY_CHAIN_MANAGER))],
) -> RedistributionRecommendationResponse:
    recommendation = decide_recommendation(db, recommendation_id, False, current_user.id, payload.note)
    return RedistributionRecommendationResponse.model_validate(recommendation)


@router.get("/inventory/surplus", response_model=CollectionResponse[RedistributionCandidateResponse])
def list_surplus(
    medicine_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
    planning_horizon_days: int = Query(default=14, ge=1, le=90),
) -> CollectionResponse[RedistributionCandidateResponse]:
    positions = get_surplus_candidates(db, medicine_id, planning_horizon_days)
    data = []
    for position in positions:
        data.append(
            RedistributionCandidateResponse(
                facility_id=position.facility_id,
                medicine_id=position.medicine_id,
                current_inventory=position.current_inventory,
                safety_stock=position.safety_stock,
                forecast_demand=position.forecast_demand,
                incoming_stock=position.incoming_stock,
                available_surplus=position.available_surplus,
                calculated_shortage=position.calculated_shortage,
            )
        )
    return CollectionResponse(
        data=data,
        pagination=Pagination(page=1, page_size=len(data) or 1, total=len(data), total_pages=1),
    )


@router.get("/inventory/shortages", response_model=CollectionResponse[RedistributionCandidateResponse])
def list_shortages(
    medicine_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
    planning_horizon_days: int = Query(default=14, ge=1, le=90),
) -> CollectionResponse[RedistributionCandidateResponse]:
    positions = get_shortage_candidates(db, medicine_id, planning_horizon_days)
    data = []
    for position in positions:
        risk = None
        from app.services.redistribution import _latest_risk_assessment
        risk_assessment = _latest_risk_assessment(db, position.facility_id, position.medicine_id)
        if risk_assessment is not None:
            risk = risk_assessment.risk_level.value
        data.append(
            RedistributionCandidateResponse(
                facility_id=position.facility_id,
                medicine_id=position.medicine_id,
                current_inventory=position.current_inventory,
                safety_stock=position.safety_stock,
                forecast_demand=position.forecast_demand,
                incoming_stock=position.incoming_stock,
                available_surplus=position.available_surplus,
                calculated_shortage=position.calculated_shortage,
                risk_level=risk,
            )
        )
    return CollectionResponse(
        data=data,
        pagination=Pagination(page=1, page_size=len(data) or 1, total=len(data), total_pages=1),
    )
