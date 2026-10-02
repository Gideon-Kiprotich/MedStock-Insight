import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class FacilityCreate(BaseModel):
    code: str = Field(min_length=2, max_length=30)
    name: str = Field(min_length=2, max_length=200)
    county: str | None = None
    facility_type: str | None = None
    transfer_eligible: bool = False

class FacilityResponse(ORMModel):
    id: uuid.UUID
    code: str
    name: str
    official_name: str | None = None
    display_name: str | None = None
    kmhfr_code: str | None = None
    county: str | None = None
    sub_county: str | None = None
    ward: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    facility_type: str | None = None
    keph_level: str | None = None
    ownership_category: str | None = None
    operational_status: str | None = None
    service_24_hour: bool | None = None
    weekend_service: bool | None = None
    bed_capacity: int | None = None
    maternity_beds: int | None = None
    icu_beds: int | None = None
    hdu_beds: int | None = None
    emergency_beds: int | None = None
    cots: int | None = None
    key_services: list[str] | None = None
    reference_note: str | None = None
    transfer_eligible: bool = False
    source_name: str | None = None
    source_url: str | None = None
    source_type: str | None = None
    source_record_id: str | None = None
    source_version: str | None = None
    retrieved_at: datetime | None = None
    verification_status: str | None = None
    is_active: bool
    created_at: datetime | None = None
