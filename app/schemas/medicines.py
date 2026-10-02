import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class MedicineCreate(BaseModel):
    code: str = Field(min_length=2, max_length=50)
    generic_name: str = Field(min_length=2, max_length=200)
    strength: str | None = None
    dosage_form: str | None = None
    category: str | None = None
    unit_of_measure: str = Field(default="unit", max_length=30)

class MedicineResponse(ORMModel):
    id: uuid.UUID
    code: str
    generic_name: str
    strength: str | None = None
    dosage_form: str | None = None
    category: str | None = None
    keml_section: str | None = None
    level_of_use: int | None = None
    aware_classification: str | None = None
    restricted: bool | None = None
    keml_notes: str | None = None
    unit_of_measure: str
    source_name: str | None = None
    source_url: str | None = None
    source_type: str | None = None
    source_record_id: str | None = None
    source_version: str | None = None
    retrieved_at: datetime | None = None
    verification_status: str | None = None
    is_active: bool
    created_at: datetime | None = None
