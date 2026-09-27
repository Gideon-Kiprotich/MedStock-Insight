from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.core import Facility, RoleCode, User
from app.schemas.common import CollectionResponse, Pagination
from app.schemas.facilities import FacilityCreate, FacilityResponse

router = APIRouter(prefix="/facilities", tags=["Facilities"])


@router.get("", response_model=CollectionResponse[FacilityResponse])
def list_facilities(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
    page: int = 1,
    page_size: int = 50,
) -> CollectionResponse[FacilityResponse]:
    page = max(page, 1)
    page_size = min(max(page_size, 1), 200)
    total = db.scalar(select(func.count()).select_from(Facility)) or 0
    items = db.scalars(
        select(Facility).order_by(Facility.name).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return CollectionResponse(
        data=[FacilityResponse.model_validate(item) for item in items],
        pagination=Pagination(page=page, page_size=page_size, total=total, total_pages=(total + page_size - 1) // page_size),
    )


@router.post("", response_model=FacilityResponse, status_code=status.HTTP_201_CREATED)
def create_facility(
    payload: FacilityCreate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(RoleCode.ADMINISTRATOR))],
) -> FacilityResponse:
    exists = db.scalar(select(Facility).where(Facility.code == payload.code.upper()))
    if exists:
        raise HTTPException(status_code=409, detail="Facility code already exists")
    facility = Facility(code=payload.code.upper(), **payload.model_dump(exclude={"code"}))
    db.add(facility)
    db.commit()
    db.refresh(facility)
    return facility
