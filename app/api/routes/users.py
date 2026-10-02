from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db
from app.models.core import Facility, Role, RoleCode, User
from app.schemas.users import DemoUserResponse

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/demo", response_model=list[DemoUserResponse])
def list_demo_users(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(RoleCode.ADMINISTRATOR))],
) -> list[DemoUserResponse]:
    rows = db.execute(
        select(User, Role, Facility)
        .join(Role, User.role_id == Role.id)
        .outerjoin(Facility, User.facility_id == Facility.id)
        .where(User.is_demo_user.is_(True))
        .order_by(User.full_name)
    ).all()
    return [
        DemoUserResponse(
            id=user.id, email=user.email, full_name=user.full_name,
            title=user.title, facility_id=user.facility_id,
            facility_name=facility.name if facility else None,
            role_code=role.code.value, role_name=role.name,
            is_active=user.is_active, last_login_at=user.last_login_at,
            is_demo_user=user.is_demo_user,
        )
        for user, role, facility in rows
    ]
