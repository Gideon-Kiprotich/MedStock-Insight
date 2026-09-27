from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.core import RiskAssessment, RiskLevel, RoleCode, User
from app.schemas.common import CollectionResponse, Pagination
from app.schemas.risk import RiskAssessmentResponse, RiskGenerateRequest
from app.services.risk import generate_risk_assessment

router = APIRouter(prefix="/risk-assessments", tags=["Risk Assessments"])


@router.post("/generate", response_model=RiskAssessmentResponse, status_code=status.HTTP_201_CREATED)
def create_risk_assessment(
    payload: RiskGenerateRequest,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(RoleCode.ADMINISTRATOR, RoleCode.SUPPLY_CHAIN_MANAGER))],
) -> RiskAssessmentResponse:
    assessment = generate_risk_assessment(
        db=db,
        facility_id=payload.facility_id,
        medicine_id=payload.medicine_id,
        forecast_run_id=payload.forecast_run_id,
    )
    return RiskAssessmentResponse.model_validate(assessment)


@router.get("", response_model=CollectionResponse[RiskAssessmentResponse])
def list_risk_assessments(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
    facility_id: UUID | None = Query(default=None),
    medicine_id: UUID | None = Query(default=None),
    risk_level: RiskLevel | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
) -> CollectionResponse[RiskAssessmentResponse]:
    filters = []
    if facility_id:
        filters.append(RiskAssessment.facility_id == facility_id)
    if medicine_id:
        filters.append(RiskAssessment.medicine_id == medicine_id)
    if risk_level:
        filters.append(RiskAssessment.risk_level == risk_level)

    query = select(RiskAssessment).where(*filters).order_by(RiskAssessment.assessed_at.desc())
    items = db.scalars(query.offset((page - 1) * page_size).limit(page_size)).all()
    total = db.scalar(select(func.count()).select_from(RiskAssessment).where(*filters)) or 0
    return CollectionResponse(
        data=[RiskAssessmentResponse.model_validate(item) for item in items],
        pagination=Pagination(
            page=page,
            page_size=page_size,
            total=total,
            total_pages=(total + page_size - 1) // page_size,
        ),
    )


@router.get("/{assessment_id}", response_model=RiskAssessmentResponse)
def get_risk_assessment(
    assessment_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
) -> RiskAssessmentResponse:
    assessment = db.get(RiskAssessment, assessment_id)
    if assessment is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Risk assessment not found")
    return RiskAssessmentResponse.model_validate(assessment)
