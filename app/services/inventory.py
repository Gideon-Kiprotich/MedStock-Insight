from datetime import date
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.core import (
    Facility,
    InventoryBalance,
    InventoryTransaction,
    InventoryTransactionType,
    Medicine,
    RoleCode,
    User,
)
from app.schemas.inventory import InventoryTransactionCreate
from app.services.audit import log_audit_event

INCREASE_TYPES = {
    InventoryTransactionType.RECEIPT,
    InventoryTransactionType.ADJUSTMENT_IN,
    InventoryTransactionType.TRANSFER_IN,
}

DECREASE_TYPES = {
    InventoryTransactionType.CONSUMPTION,
    InventoryTransactionType.ADJUSTMENT_OUT,
    InventoryTransactionType.TRANSFER_OUT,
}


def record_inventory_transaction(
    db: Session,
    payload: InventoryTransactionCreate,
    current_user: User,
) -> InventoryTransaction:
    if (current_user.role.code == RoleCode.INVENTORY_OFFICER
            and current_user.facility_id != payload.facility_id):
        raise HTTPException(status_code=403, detail="Inventory officers may record only their assigned facility")
    if payload.transaction_type in {InventoryTransactionType.TRANSFER_IN, InventoryTransactionType.TRANSFER_OUT}:
        raise HTTPException(status_code=422, detail="Transfer movements must use the approved transfer workflow")
    facility = db.scalar(select(Facility).where(Facility.id == payload.facility_id, Facility.is_active.is_(True)).with_for_update().execution_options(populate_existing=True))
    medicine = db.scalar(select(Medicine).where(Medicine.id == payload.medicine_id, Medicine.is_active.is_(True)))
    if facility is None:
        raise HTTPException(status_code=404, detail="Facility not found")
    if medicine is None:
        raise HTTPException(status_code=404, detail="Medicine not found")

    balance = db.scalar(
        select(InventoryBalance)
        .where(
            InventoryBalance.facility_id == payload.facility_id,
            InventoryBalance.medicine_id == payload.medicine_id,
        )
        .with_for_update().execution_options(populate_existing=True)
    )
    if balance is None:
        balance = InventoryBalance(
            facility_id=payload.facility_id,
            medicine_id=payload.medicine_id,
            quantity_on_hand=Decimal("0"),
        )
        db.add(balance)
        db.flush()

    current = Decimal(balance.quantity_on_hand)
    if payload.transaction_type in INCREASE_TYPES:
        new_quantity = current + payload.quantity
    elif payload.transaction_type in DECREASE_TYPES:
        new_quantity = current - payload.quantity
        if new_quantity < 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Transaction would make inventory negative",
            )
    else:
        raise HTTPException(status_code=400, detail="Unsupported transaction type")

    transaction = InventoryTransaction(
        facility_id=payload.facility_id,
        medicine_id=payload.medicine_id,
        transaction_type=payload.transaction_type,
        quantity=payload.quantity,
        transaction_date=payload.transaction_date or date.today(),
        reference_number=payload.reference_number,
        notes=payload.notes,
        created_by=current_user.id,
    )
    balance.quantity_on_hand = new_quantity
    db.add(transaction)
    db.flush()
    log_audit_event(db=db, user_id=current_user.id, action="INVENTORY_TRANSACTION_CREATED",
                    entity_type="inventory_transaction", entity_id=transaction.id, new_state={"transaction_type": transaction.transaction_type.value,
                    "quantity": str(transaction.quantity), "facility_id": str(transaction.facility_id)})
    db.commit()
    db.refresh(transaction)
    return transaction
