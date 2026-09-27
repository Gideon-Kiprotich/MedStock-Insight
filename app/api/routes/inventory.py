from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.core import InventoryBalance, InventoryTransaction, RoleCode, User
from app.schemas.common import CollectionResponse, Pagination
from app.schemas.inventory import (
    InventoryBalanceResponse,
    InventoryTransactionCreate,
    InventoryTransactionResponse,
)
from app.services.inventory import record_inventory_transaction

router = APIRouter(prefix="/inventory", tags=["Inventory"])


@router.get("", response_model=CollectionResponse[InventoryBalanceResponse])
def list_inventory(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
    facility_id: UUID | None = Query(default=None),
    medicine_id: UUID | None = Query(default=None),
    page: int = 1,
    page_size: int = 50,
) -> CollectionResponse[InventoryBalanceResponse]:
    filters = []
    if facility_id:
        filters.append(InventoryBalance.facility_id == facility_id)
    if medicine_id:
        filters.append(InventoryBalance.medicine_id == medicine_id)

    page = max(page, 1)
    page_size = min(max(page_size, 1), 200)
    count_query = select(func.count()).select_from(InventoryBalance).where(*filters)
    total = db.scalar(count_query) or 0
    items = db.scalars(
        select(InventoryBalance).where(*filters).order_by(InventoryBalance.updated_at.desc())
        .offset((page - 1) * page_size).limit(page_size)
    ).all()
    return CollectionResponse(
        data=[InventoryBalanceResponse.model_validate(item) for item in items],
        pagination=Pagination(page=page, page_size=page_size, total=total, total_pages=(total + page_size - 1) // page_size),
    )


@router.get("/transactions", response_model=CollectionResponse[InventoryTransactionResponse])
def list_transactions(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
    facility_id: UUID | None = Query(default=None),
    medicine_id: UUID | None = Query(default=None),
    page: int = 1,
    page_size: int = 50,
) -> CollectionResponse[InventoryTransactionResponse]:
    filters = []
    if facility_id:
        filters.append(InventoryTransaction.facility_id == facility_id)
    if medicine_id:
        filters.append(InventoryTransaction.medicine_id == medicine_id)

    page = max(page, 1)
    page_size = min(max(page_size, 1), 200)
    total = db.scalar(select(func.count()).select_from(InventoryTransaction).where(*filters)) or 0
    items = db.scalars(
        select(InventoryTransaction).where(*filters)
        .order_by(InventoryTransaction.transaction_date.desc(), InventoryTransaction.created_at.desc())
        .offset((page - 1) * page_size).limit(page_size)
    ).all()
    return CollectionResponse(
        data=[InventoryTransactionResponse.model_validate(item) for item in items],
        pagination=Pagination(page=page, page_size=page_size, total=total, total_pages=(total + page_size - 1) // page_size),
    )


@router.post("/transactions", response_model=InventoryTransactionResponse, status_code=status.HTTP_201_CREATED)
def create_transaction(
    payload: InventoryTransactionCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleCode.ADMINISTRATOR, RoleCode.INVENTORY_OFFICER))],
) -> InventoryTransactionResponse:
    return record_inventory_transaction(db, payload, current_user)
