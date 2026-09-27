import uuid

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
    strength: str | None
    dosage_form: str | None
    category: str | None
    unit_of_measure: str
    is_active: bool
