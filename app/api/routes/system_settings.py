from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.core import RoleCode, User
from app.schemas.settings import SystemSettingsResponse, SystemSettingsUpdate
from app.services.system_settings import get_system_settings, update_system_settings

router = APIRouter(prefix="/settings", tags=["System Settings"])


@router.get("", response_model=SystemSettingsResponse)
def read_settings(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
) -> SystemSettingsResponse:
    return get_system_settings(db)


@router.post("", response_model=SystemSettingsResponse)
def change_settings(
    payload: SystemSettingsUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(RoleCode.ADMINISTRATOR))],
) -> SystemSettingsResponse:
    return update_system_settings(db, payload, current_user)
