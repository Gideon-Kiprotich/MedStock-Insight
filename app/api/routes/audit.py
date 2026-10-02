from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.core import AuditLog, RoleCode, User
from app.schemas.audit import AuditLogResponse
from app.schemas.common import CollectionResponse, Pagination

router = APIRouter(prefix="/audit", tags=["Audit Logs"])


@router.get("", response_model=CollectionResponse[AuditLogResponse])
def list_audit_logs(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[
        User,
        Depends(
            require_roles(
                RoleCode.ADMINISTRATOR, RoleCode.SUPPLY_CHAIN_MANAGER, RoleCode.INVENTORY_OFFICER
            )
        ),
    ],
    action: str | None = None,
    entity_type: str | None = None,
    entity_id: UUID | None = None,
    user_id: UUID | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
) -> CollectionResponse[AuditLogResponse]:
    filters = []
    if action:
        filters.append(AuditLog.action == action)
    if entity_type:
        filters.append(AuditLog.entity_type == entity_type)
    if entity_id:
        filters.append(AuditLog.entity_id == entity_id)
    if user_id:
        filters.append(AuditLog.user_id == user_id)

    query = select(AuditLog).where(*filters).order_by(AuditLog.timestamp.desc())
    items = db.scalars(query.offset((page - 1) * page_size).limit(page_size)).all()
    total = db.scalar(select(func.count()).select_from(AuditLog).where(*filters)) or 0
    return CollectionResponse(
        data=[AuditLogResponse.model_validate(item) for item in items],
        pagination=Pagination(
            page=page,
            page_size=page_size,
            total=total,
            total_pages=(total + page_size - 1) // page_size if total > 0 else 1,
        ),
    )
