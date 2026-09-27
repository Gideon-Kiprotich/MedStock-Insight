from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.models.core import ForecastModelCode


class MLModelVersionResponse(BaseModel):
    id: UUID
    code: ForecastModelCode
    name: str
    algorithm: str
    version: str
    hyperparameters: dict | None
    evaluation_metrics: dict | None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
