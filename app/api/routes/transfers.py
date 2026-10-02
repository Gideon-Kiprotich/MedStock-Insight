from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.core import RedistributionTransfer, RedistributionTransferStatus, RoleCode, User
from app.schemas.common import CollectionResponse, Pagination
from app.schemas.transfers import TransferCancel, TransferCreate, TransferResponse
from app.services.transfer import (
    cancel_transfer,
    complete_transfer,
    create_transfer,
    dispatch_transfer,
    get_transfer,
)

router = APIRouter(prefix="/transfers", tags=["Transfers"])


@router.post("", response_model=TransferResponse, status_code=status.HTTP_201_CREATED)
def create_transfer_endpoint(
    payload: TransferCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[
        User, Depends(require_roles(RoleCode.ADMINISTRATOR, RoleCode.SUPPLY_CHAIN_MANAGER))
    ],
) -> TransferResponse:
    transfer = create_transfer(db=db, payload=payload, current_user=current_user)
    return TransferResponse.model_validate(transfer)


@router.get("", response_model=CollectionResponse[TransferResponse])
def list_transfers_endpoint(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
    status_filter: RedistributionTransferStatus | None = Query(default=None, alias="status"),
    source_facility_id: UUID | None = None,
    destination_facility_id: UUID | None = None,
    medicine_id: UUID | None = None,
    recommendation_id: UUID | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
) -> CollectionResponse[TransferResponse]:
    filters = []
    if status_filter:
        filters.append(RedistributionTransfer.status == status_filter)
    if source_facility_id:
        filters.append(RedistributionTransfer.source_facility_id == source_facility_id)
    if destination_facility_id:
        filters.append(RedistributionTransfer.destination_facility_id == destination_facility_id)
    if medicine_id:
        filters.append(RedistributionTransfer.medicine_id == medicine_id)
    if recommendation_id:
        filters.append(RedistributionTransfer.recommendation_id == recommendation_id)

    query = (
        select(RedistributionTransfer)
        .where(*filters)
        .order_by(RedistributionTransfer.created_at.desc())
    )
    items = db.scalars(query.offset((page - 1) * page_size).limit(page_size)).all()
    total = db.scalar(select(func.count()).select_from(RedistributionTransfer).where(*filters)) or 0
    return CollectionResponse(
        data=[TransferResponse.model_validate(item) for item in items],
        pagination=Pagination(
            page=page,
            page_size=page_size,
            total=total,
            total_pages=(total + page_size - 1) // page_size if total > 0 else 1,
        ),
    )


@router.get("/{transfer_id}", response_model=TransferResponse)
def get_transfer_endpoint(
    transfer_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
) -> TransferResponse:
    transfer = get_transfer(db=db, transfer_id=transfer_id)
    return TransferResponse.model_validate(transfer)


@router.post("/{transfer_id}/dispatch", response_model=TransferResponse)
def dispatch_transfer_endpoint(
    transfer_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[
        User, Depends(require_roles(RoleCode.ADMINISTRATOR, RoleCode.SUPPLY_CHAIN_MANAGER))
    ],
) -> TransferResponse:
    transfer = dispatch_transfer(db=db, transfer_id=transfer_id, current_user=current_user)
    return TransferResponse.model_validate(transfer)


@router.post("/{transfer_id}/complete", response_model=TransferResponse)
def complete_transfer_endpoint(
    transfer_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[
        User,
        Depends(
            require_roles(
                RoleCode.ADMINISTRATOR, RoleCode.SUPPLY_CHAIN_MANAGER, RoleCode.INVENTORY_OFFICER
            )
        ),
    ],
) -> TransferResponse:
    transfer = complete_transfer(db=db, transfer_id=transfer_id, current_user=current_user)
    return TransferResponse.model_validate(transfer)


@router.post("/{transfer_id}/cancel", response_model=TransferResponse)
def cancel_transfer_endpoint(
    transfer_id: UUID,
    payload: TransferCancel,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[
        User, Depends(require_roles(RoleCode.ADMINISTRATOR, RoleCode.SUPPLY_CHAIN_MANAGER))
    ],
) -> TransferResponse:
    transfer = cancel_transfer(
        db=db, transfer_id=transfer_id, current_user=current_user, reason=payload.reason
    )
    return TransferResponse.model_validate(transfer)
