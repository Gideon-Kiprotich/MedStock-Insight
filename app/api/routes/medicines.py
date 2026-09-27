from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.core import Medicine, RoleCode, User
from app.schemas.common import CollectionResponse, Pagination
from app.schemas.medicines import MedicineCreate, MedicineResponse

router = APIRouter(prefix="/medicines", tags=["Medicines"])


@router.get("", response_model=CollectionResponse[MedicineResponse])
def list_medicines(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
    page: int = 1,
    page_size: int = 50,
) -> CollectionResponse[MedicineResponse]:
    page = max(page, 1)
    page_size = min(max(page_size, 1), 200)
    total = db.scalar(select(func.count()).select_from(Medicine)) or 0
    items = db.scalars(
        select(Medicine).order_by(Medicine.generic_name).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return CollectionResponse(
        data=[MedicineResponse.model_validate(item) for item in items],
        pagination=Pagination(page=page, page_size=page_size, total=total, total_pages=(total + page_size - 1) // page_size),
    )


@router.post("", response_model=MedicineResponse, status_code=status.HTTP_201_CREATED)
def create_medicine(
    payload: MedicineCreate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(RoleCode.ADMINISTRATOR))],
) -> MedicineResponse:
    exists = db.scalar(select(Medicine).where(Medicine.code == payload.code.upper()))
    if exists:
        raise HTTPException(status_code=409, detail="Medicine code already exists")
    medicine = Medicine(code=payload.code.upper(), **payload.model_dump(exclude={"code"}))
    db.add(medicine)
    db.commit()
    db.refresh(medicine)
    return medicine
