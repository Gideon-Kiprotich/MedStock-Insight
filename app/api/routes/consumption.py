from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.core import User
from app.schemas.consumption import (
    ConsumptionResponse,
    ConsumptionSortField,
    ConsumptionSortOrder,
)
from app.services.consumption import list_consumption

router = APIRouter(prefix="/consumption", tags=["Consumption"])


@router.get("", response_model=ConsumptionResponse)
def get_consumption_log(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    facility_id: UUID | None = Query(default=None),
    medicine_id: UUID | None = Query(default=None),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    search: str | None = Query(default=None, max_length=120),
    sort_by: ConsumptionSortField = Query(default="transaction_date"),
    sort_order: ConsumptionSortOrder = Query(default="desc"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=200),
) -> ConsumptionResponse:
    return list_consumption(
        db,
        current_user,
        facility_id=facility_id,
        medicine_id=medicine_id,
        start_date=start_date,
        end_date=end_date,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size,
    )
