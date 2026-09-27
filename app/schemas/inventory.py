import uuid
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.core import InventoryTransactionType
from app.schemas.common import ORMModel


class InventoryTransactionCreate(BaseModel):
    facility_id: uuid.UUID
    medicine_id: uuid.UUID
    transaction_type: InventoryTransactionType
    quantity: Decimal = Field(gt=0)
    transaction_date: date
    reference_number: str | None = None
    notes: str | None = None


class InventoryTransactionResponse(ORMModel):
    id: uuid.UUID
    facility_id: uuid.UUID
    medicine_id: uuid.UUID
    transaction_type: InventoryTransactionType
    quantity: Decimal
    transaction_date: date
    reference_number: str | None
    notes: str | None
    created_by: uuid.UUID


class InventoryBalanceResponse(ORMModel):
    id: uuid.UUID
    facility_id: uuid.UUID
    medicine_id: uuid.UUID
    quantity_on_hand: Decimal


class InventoryQuery(BaseModel):
    facility_id: uuid.UUID | None = None
    medicine_id: uuid.UUID | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=200)
