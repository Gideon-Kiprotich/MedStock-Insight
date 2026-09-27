import uuid

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class FacilityCreate(BaseModel):
    code: str = Field(min_length=2, max_length=30)
    name: str = Field(min_length=2, max_length=200)
    county: str | None = None
    facility_type: str | None = None


class FacilityResponse(ORMModel):
    id: uuid.UUID
    code: str
    name: str
    county: str | None
    facility_type: str | None
    is_active: bool
