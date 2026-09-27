from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.core import MLModelVersion, User
from app.schemas.models import MLModelVersionResponse

router = APIRouter(prefix="/models", tags=["Models"])


@router.get("", response_model=list[MLModelVersionResponse])
def list_models(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
) -> list[MLModelVersionResponse]:
    items = db.scalars(select(MLModelVersion).order_by(MLModelVersion.created_at.desc())).all()
    return [MLModelVersionResponse.model_validate(item) for item in items]
