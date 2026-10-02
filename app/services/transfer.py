from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.core import (
    Batch,
    Facility,
    FacilityMedicinePolicy,
    InventoryBalance,
    InventoryTransaction,
    InventoryTransactionType,
    Medicine,
    RedistributionRecommendation,
    RedistributionRecommendationStatus,
    RedistributionTransfer,
    RedistributionTransferStatus,
    User,
)
from app.schemas.transfers import TransferCreate
from app.services.audit import log_audit_event


def _ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def create_transfer(
    db: Session,
    payload: TransferCreate,
    current_user: User,
) -> RedistributionTransfer:
    recommendation = db.get(RedistributionRecommendation, payload.recommendation_id)
    if recommendation is None:
        raise HTTPException(status_code=404, detail="Redistribution recommendation not found")

    if recommendation.status != RedistributionRecommendationStatus.APPROVED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot create transfer for recommendation with status '{recommendation.status.value}'",
        )

    now = datetime.now(timezone.utc)
    if _ensure_utc(recommendation.expires_at) <= now:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Redistribution recommendation has expired",
        )

    existing_transfer = db.scalar(
        select(RedistributionTransfer).where(
            RedistributionTransfer.recommendation_id == recommendation.id,
            RedistributionTransfer.status.in_(
                [
                    RedistributionTransferStatus.APPROVED,
                    RedistributionTransferStatus.IN_TRANSIT,
                    RedistributionTransferStatus.COMPLETED,
                ]
            ),
        )
    )
    if existing_transfer is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A transfer has already been created for this recommendation",
        )

    if payload.quantity <= Decimal("0"):
        raise HTTPException(status_code=400, detail="Transfer quantity must be greater than zero")

    if payload.quantity > recommendation.recommended_quantity:
        raise HTTPException(
            status_code=400,
            detail=f"Transfer quantity {payload.quantity} exceeds recommended quantity {recommendation.recommended_quantity}",
        )

    source_balance = db.scalar(
        select(InventoryBalance)
        .where(
            InventoryBalance.facility_id == recommendation.source_facility_id,
            InventoryBalance.medicine_id == recommendation.medicine_id,
        )
        .with_for_update()
    )
    available_stock = Decimal(source_balance.quantity_on_hand) if source_balance else Decimal("0")
    if payload.quantity > available_stock:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Transfer quantity {payload.quantity} exceeds available source inventory {available_stock}",
        )

    batch: Batch | None = None
    if payload.batch_id is not None:
        batch = db.get(Batch, payload.batch_id)
        if batch is None:
            raise HTTPException(status_code=404, detail="Batch not found")
        if batch.facility_id != recommendation.source_facility_id:
            raise HTTPException(status_code=400, detail="Batch does not belong to the source facility")
        if batch.medicine_id != recommendation.medicine_id:
            raise HTTPException(status_code=400, detail="Batch does not match the transfer medicine")
        if payload.quantity > Decimal(batch.quantity):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Transfer quantity {payload.quantity} exceeds available batch quantity {batch.quantity}",
            )

    transfer = RedistributionTransfer(
        recommendation_id=recommendation.id,
        source_facility_id=recommendation.source_facility_id,
        destination_facility_id=recommendation.destination_facility_id,
        medicine_id=recommendation.medicine_id,
        batch_id=batch.id if batch else None,
        quantity=payload.quantity,
        status=RedistributionTransferStatus.APPROVED,
        approved_by=current_user.id,
        approved_at=now,
    )
    db.add(transfer)
    db.flush()

    log_audit_event(
        db=db,
        user_id=current_user.id,
        action="TRANSFER_CREATED",
        entity_type="redistribution_transfer",
        entity_id=transfer.id,
        new_state={"status": transfer.status.value, "quantity": str(transfer.quantity)},
        details={
            "recommendation_id": str(recommendation.id),
            "source_facility_id": str(transfer.source_facility_id),
            "destination_facility_id": str(transfer.destination_facility_id),
            "medicine_id": str(transfer.medicine_id),
            "batch_id": str(transfer.batch_id) if transfer.batch_id else None,
        },
    )

    db.commit()
    db.refresh(transfer)
    return transfer


def dispatch_transfer(
    db: Session,
    transfer_id: UUID,
    current_user: User,
) -> RedistributionTransfer:
    transfer = db.get(RedistributionTransfer, transfer_id)
    if transfer is None:
        raise HTTPException(status_code=404, detail="Transfer not found")

    # Idempotency check: If already dispatched (IN_TRANSIT), return idempotently without duplicate inventory movement
    if transfer.status == RedistributionTransferStatus.IN_TRANSIT:
        return transfer

    if transfer.status != RedistributionTransferStatus.APPROVED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot dispatch transfer with status '{transfer.status.value}'",
        )

    recommendation = db.get(RedistributionRecommendation, transfer.recommendation_id)
    if recommendation is None or recommendation.status != RedistributionRecommendationStatus.APPROVED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Associated recommendation is no longer valid or approved",
        )

    now = datetime.now(timezone.utc)
    if _ensure_utc(recommendation.expires_at) <= now:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Associated recommendation has expired",
        )

    source_policy = db.scalar(
        select(FacilityMedicinePolicy).where(
            FacilityMedicinePolicy.facility_id == transfer.source_facility_id,
            FacilityMedicinePolicy.medicine_id == transfer.medicine_id,
        )
    )

    source_balance = db.scalar(
        select(InventoryBalance)
        .where(
            InventoryBalance.facility_id == transfer.source_facility_id,
            InventoryBalance.medicine_id == transfer.medicine_id,
        )
        .with_for_update()
    )
    current_stock = Decimal(source_balance.quantity_on_hand) if source_balance else Decimal("0")
    if current_stock < transfer.quantity:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Insufficient source inventory ({current_stock}) to dispatch {transfer.quantity}",
        )

    if source_policy and (current_stock - transfer.quantity < Decimal(source_policy.safety_stock)):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Dispatch would breach source facility safety stock constraint",
        )

    if transfer.batch_id is not None:
        batch = db.scalar(
            select(Batch).where(Batch.id == transfer.batch_id).with_for_update()
        )
        if batch is None or Decimal(batch.quantity) < transfer.quantity:
            batch_qty = Decimal(batch.quantity) if batch else Decimal("0")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Insufficient batch quantity ({batch_qty}) to dispatch {transfer.quantity}",
            )
        batch.quantity = Decimal(batch.quantity) - transfer.quantity

    source_balance.quantity_on_hand = current_stock - transfer.quantity

    tx_out = InventoryTransaction(
        facility_id=transfer.source_facility_id,
        medicine_id=transfer.medicine_id,
        transaction_type=InventoryTransactionType.TRANSFER_OUT,
        quantity=transfer.quantity,
        transaction_date=date.today(),
        reference_number=f"TRANSFER-OUT-{transfer.id}",
        notes=f"Dispatched transfer {transfer.id}",
        created_by=current_user.id,
    )
    db.add(tx_out)
    db.flush()

    prev_status = transfer.status.value
    transfer.status = RedistributionTransferStatus.IN_TRANSIT
    transfer.dispatched_by = current_user.id
    transfer.dispatched_at = now

    log_audit_event(
        db=db,
        user_id=current_user.id,
        action="TRANSFER_DISPATCHED",
        entity_type="redistribution_transfer",
        entity_id=transfer.id,
        previous_state={"status": prev_status},
        new_state={"status": transfer.status.value},
        details={"dispatched_at": now.isoformat()},
    )

    log_audit_event(
        db=db,
        user_id=current_user.id,
        action="INVENTORY_TRANSFER_OUT",
        entity_type="inventory_transaction",
        entity_id=tx_out.id,
        new_state={
            "facility_id": str(transfer.source_facility_id),
            "medicine_id": str(transfer.medicine_id),
            "quantity": str(transfer.quantity),
            "transaction_type": InventoryTransactionType.TRANSFER_OUT.value,
        },
        details={"transfer_id": str(transfer.id)},
    )

    db.commit()
    db.refresh(transfer)
    return transfer


def complete_transfer(
    db: Session,
    transfer_id: UUID,
    current_user: User,
) -> RedistributionTransfer:
    transfer = db.get(RedistributionTransfer, transfer_id)
    if transfer is None:
        raise HTTPException(status_code=404, detail="Transfer not found")

    # Idempotency check: If already COMPLETED, return idempotently without duplicate inventory movement
    if transfer.status == RedistributionTransferStatus.COMPLETED:
        return transfer

    if transfer.status != RedistributionTransferStatus.IN_TRANSIT:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot complete transfer with status '{transfer.status.value}'",
        )

    now = datetime.now(timezone.utc)

    dest_balance = db.scalar(
        select(InventoryBalance)
        .where(
            InventoryBalance.facility_id == transfer.destination_facility_id,
            InventoryBalance.medicine_id == transfer.medicine_id,
        )
        .with_for_update()
    )
    if dest_balance is None:
        dest_balance = InventoryBalance(
            facility_id=transfer.destination_facility_id,
            medicine_id=transfer.medicine_id,
            quantity_on_hand=Decimal("0.00"),
        )
        db.add(dest_balance)
        db.flush()

    dest_balance.quantity_on_hand = Decimal(dest_balance.quantity_on_hand) + transfer.quantity

    if transfer.batch_id is not None:
        source_batch = db.get(Batch, transfer.batch_id)
        if source_batch is not None:
            dest_batch = db.scalar(
                select(Batch)
                .where(
                    Batch.facility_id == transfer.destination_facility_id,
                    Batch.medicine_id == transfer.medicine_id,
                    Batch.batch_number == source_batch.batch_number,
                )
                .with_for_update()
            )
            if dest_batch is None:
                dest_batch = Batch(
                    facility_id=transfer.destination_facility_id,
                    medicine_id=transfer.medicine_id,
                    batch_number=source_batch.batch_number,
                    expiry_date=source_batch.expiry_date,
                    quantity=transfer.quantity,
                )
                db.add(dest_batch)
                db.flush()
            else:
                dest_batch.quantity = Decimal(dest_batch.quantity) + transfer.quantity

    tx_in = InventoryTransaction(
        facility_id=transfer.destination_facility_id,
        medicine_id=transfer.medicine_id,
        transaction_type=InventoryTransactionType.TRANSFER_IN,
        quantity=transfer.quantity,
        transaction_date=date.today(),
        reference_number=f"TRANSFER-IN-{transfer.id}",
        notes=f"Received transfer {transfer.id}",
        created_by=current_user.id,
    )
    db.add(tx_in)
    db.flush()

    prev_status = transfer.status.value
    transfer.status = RedistributionTransferStatus.COMPLETED
    transfer.received_by = current_user.id
    transfer.received_at = now

    log_audit_event(
        db=db,
        user_id=current_user.id,
        action="TRANSFER_COMPLETED",
        entity_type="redistribution_transfer",
        entity_id=transfer.id,
        previous_state={"status": prev_status},
        new_state={"status": transfer.status.value},
        details={"received_at": now.isoformat()},
    )

    log_audit_event(
        db=db,
        user_id=current_user.id,
        action="INVENTORY_TRANSFER_IN",
        entity_type="inventory_transaction",
        entity_id=tx_in.id,
        new_state={
            "facility_id": str(transfer.destination_facility_id),
            "medicine_id": str(transfer.medicine_id),
            "quantity": str(transfer.quantity),
            "transaction_type": InventoryTransactionType.TRANSFER_IN.value,
        },
        details={"transfer_id": str(transfer.id)},
    )

    db.commit()
    db.refresh(transfer)
    return transfer


def cancel_transfer(
    db: Session,
    transfer_id: UUID,
    current_user: User,
    reason: str | None = None,
) -> RedistributionTransfer:
    transfer = db.get(RedistributionTransfer, transfer_id)
    if transfer is None:
        raise HTTPException(status_code=404, detail="Transfer not found")

    if transfer.status == RedistributionTransferStatus.CANCELLED:
        return transfer

    if transfer.status == RedistributionTransferStatus.IN_TRANSIT:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot cancel transfer in IN_TRANSIT status. Stock has already dispatched from the source facility.",
        )

    if transfer.status != RedistributionTransferStatus.APPROVED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot cancel transfer with status '{transfer.status.value}'",
        )

    now = datetime.now(timezone.utc)
    prev_status = transfer.status.value
    transfer.status = RedistributionTransferStatus.CANCELLED
    transfer.cancelled_by = current_user.id
    transfer.cancelled_at = now
    transfer.cancellation_reason = reason

    log_audit_event(
        db=db,
        user_id=current_user.id,
        action="TRANSFER_CANCELLED",
        entity_type="redistribution_transfer",
        entity_id=transfer.id,
        previous_state={"status": prev_status},
        new_state={"status": transfer.status.value},
        details={"cancellation_reason": reason, "cancelled_at": now.isoformat()},
    )

    db.commit()
    db.refresh(transfer)
    return transfer


def get_transfer(db: Session, transfer_id: UUID) -> RedistributionTransfer:
    transfer = db.get(RedistributionTransfer, transfer_id)
    if transfer is None:
        raise HTTPException(status_code=404, detail="Transfer not found")
    return transfer
