from datetime import date
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.core import (
    Facility,
    InventoryTransaction,
    InventoryTransactionType,
    Medicine,
    RoleCode,
    User,
)
from app.schemas.common import Pagination
from app.schemas.consumption import (
    ConsumptionEntryResponse,
    ConsumptionResponse,
    ConsumptionSortField,
    ConsumptionSortOrder,
    ConsumptionSummaryResponse,
    ConsumptionTrendPointResponse,
)


def _medicine_name(medicine: Medicine) -> str:
    return f"{medicine.generic_name} {medicine.strength or ''} {medicine.dosage_form or ''}".strip()


def _search_pattern(value: str) -> str:
    escaped = value.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def list_consumption(
    db: Session,
    current_user: User,
    *,
    facility_id: UUID | None = None,
    medicine_id: UUID | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    search: str | None = None,
    sort_by: ConsumptionSortField = "transaction_date",
    sort_order: ConsumptionSortOrder = "desc",
    page: int = 1,
    page_size: int = 25,
) -> ConsumptionResponse:
    if start_date and end_date and start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="start_date must be on or before end_date",
        )
    if current_user.role.code == RoleCode.INVENTORY_OFFICER:
        if current_user.facility_id is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Inventory officer is not assigned to a facility",
            )
        if facility_id is not None and facility_id != current_user.facility_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Inventory officers may view only their assigned facility",
            )
        facility_id = current_user.facility_id

    filters = [InventoryTransaction.transaction_type == InventoryTransactionType.CONSUMPTION]
    if facility_id:
        filters.append(InventoryTransaction.facility_id == facility_id)
    if medicine_id:
        filters.append(InventoryTransaction.medicine_id == medicine_id)
    if start_date:
        filters.append(InventoryTransaction.transaction_date >= start_date)
    if end_date:
        filters.append(InventoryTransaction.transaction_date <= end_date)
    if search and search.strip():
        pattern = _search_pattern(search)
        filters.append(
            Facility.name.ilike(pattern, escape="\\")
            | Medicine.generic_name.ilike(pattern, escape="\\")
            | Medicine.code.ilike(pattern, escape="\\")
            | InventoryTransaction.reference_number.ilike(pattern, escape="\\")
            | InventoryTransaction.notes.ilike(pattern, escape="\\")
            | User.full_name.ilike(pattern, escape="\\")
        )

    joins = (
        InventoryTransaction,
        Facility,
        Medicine,
        User,
    )
    base = (
        select(*joins)
        .join(Facility, InventoryTransaction.facility_id == Facility.id)
        .join(Medicine, InventoryTransaction.medicine_id == Medicine.id)
        .join(User, InventoryTransaction.created_by == User.id)
        .where(*filters)
    )
    count_query = (
        select(func.count())
        .select_from(InventoryTransaction)
        .join(Facility, InventoryTransaction.facility_id == Facility.id)
        .join(Medicine, InventoryTransaction.medicine_id == Medicine.id)
        .join(User, InventoryTransaction.created_by == User.id)
        .where(*filters)
    )

    page = max(page, 1)
    page_size = min(max(page_size, 1), 200)
    total = db.scalar(count_query) or 0

    sort_columns = {
        "transaction_date": InventoryTransaction.transaction_date,
        "quantity": InventoryTransaction.quantity,
        "facility_name": Facility.name,
        "medicine_name": Medicine.generic_name,
        "created_at": InventoryTransaction.created_at,
    }
    sort_column = sort_columns[sort_by]
    order_clause = sort_column.asc() if sort_order == "asc" else sort_column.desc()
    rows = db.execute(
        base.order_by(order_clause, InventoryTransaction.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    entries = [
        ConsumptionEntryResponse(
            id=transaction.id,
            facility_id=transaction.facility_id,
            facility_name=facility.name,
            medicine_id=transaction.medicine_id,
            medicine_name=_medicine_name(medicine),
            unit_of_measure=medicine.unit_of_measure,
            quantity=transaction.quantity,
            transaction_date=transaction.transaction_date,
            reference_number=transaction.reference_number,
            notes=transaction.notes,
            recorded_by=transaction.created_by,
            recorded_by_name=recorder.full_name,
            created_at=transaction.created_at,
        )
        for transaction, facility, medicine, recorder in rows
    ]

    (
        total_quantity,
        transaction_count,
        distinct_medicines,
        first_date,
        last_date,
    ) = db.execute(
        select(
            func.coalesce(func.sum(InventoryTransaction.quantity), 0),
            func.count(InventoryTransaction.id),
            func.count(func.distinct(InventoryTransaction.medicine_id)),
            func.min(InventoryTransaction.transaction_date),
            func.max(InventoryTransaction.transaction_date),
        )
        .select_from(InventoryTransaction)
        .join(Facility, InventoryTransaction.facility_id == Facility.id)
        .join(Medicine, InventoryTransaction.medicine_id == Medicine.id)
        .join(User, InventoryTransaction.created_by == User.id)
        .where(*filters)
    ).one()
    total_quantity = Decimal(str(total_quantity or 0))
    transaction_count = int(transaction_count or 0)
    distinct_medicines = int(distinct_medicines or 0)
    days_covered = (last_date - first_date).days + 1 if first_date and last_date else 0
    daily_average = (
        (total_quantity / Decimal(days_covered)).quantize(Decimal("0.01"))
        if days_covered
        else Decimal("0.00")
    )
    summary = ConsumptionSummaryResponse(
        total_quantity=total_quantity,
        transaction_count=transaction_count,
        distinct_medicines=distinct_medicines,
        days_covered=days_covered,
        daily_average=daily_average,
        first_date=first_date,
        last_date=last_date,
    )
    trend = [
        ConsumptionTrendPointResponse(
            date=trend_date,
            quantity=trend_quantity,
            transaction_count=trend_count,
        )
        for trend_date, trend_quantity, trend_count in db.execute(
            select(
                InventoryTransaction.transaction_date,
                func.sum(InventoryTransaction.quantity),
                func.count(InventoryTransaction.id),
            )
            .select_from(InventoryTransaction)
            .join(Facility, InventoryTransaction.facility_id == Facility.id)
            .join(Medicine, InventoryTransaction.medicine_id == Medicine.id)
            .join(User, InventoryTransaction.created_by == User.id)
            .where(*filters)
            .group_by(InventoryTransaction.transaction_date)
            .order_by(InventoryTransaction.transaction_date)
        ).all()
    ]
    return ConsumptionResponse(
        data=entries,
        pagination=Pagination(
            page=page,
            page_size=page_size,
            total=total,
            total_pages=(total + page_size - 1) // page_size,
        ),
        summary=summary,
        trend=trend,
    )
