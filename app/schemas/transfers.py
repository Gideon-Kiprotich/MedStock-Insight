from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.core import RedistributionTransferStatus
from app.schemas.common import ORMModel


class TransferCreate(BaseModel):
    recommendation_id: UUID
    batch_id: UUID | None = None
    quantity: Decimal = Field(gt=Decimal("0"))


class TransferCancel(BaseModel):
    reason: str | None = Field(default=None, max_length=1000)


class TransferResponse(ORMModel):
    id: UUID
    recommendation_id: UUID
    source_facility_id: UUID
    destination_facility_id: UUID
    medicine_id: UUID
    batch_id: UUID | None
    quantity: Decimal
    status: RedistributionTransferStatus
    approved_by: UUID
    approved_at: datetime
    dispatched_by: UUID | None
    dispatched_at: datetime | None
    received_by: UUID | None
    received_at: datetime | None
    cancelled_by: UUID | None
    cancelled_at: datetime | None
    cancellation_reason: str | None
    created_at: datetime
    updated_at: datetime
