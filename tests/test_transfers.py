from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import uuid

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.models.core import (
    AuditLog,
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
    Role,
    RoleCode,
    User,
)
from app.schemas.transfers import TransferCancel, TransferCreate
from app.services.redistribution import decide_recommendation
from app.services.transfer import (
    cancel_transfer,
    complete_transfer,
    create_transfer,
    dispatch_transfer,
)


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = testing_session_local()

    # Seed roles
    role_admin = Role(id=uuid.uuid4(), code=RoleCode.ADMINISTRATOR, name="Admin")
    role_scm = Role(id=uuid.uuid4(), code=RoleCode.SUPPLY_CHAIN_MANAGER, name="Supply Chain Manager")
    role_io = Role(id=uuid.uuid4(), code=RoleCode.INVENTORY_OFFICER, name="Inventory Officer")
    session.add_all([role_admin, role_scm, role_io])

    # Seed users
    admin_user = User(
        id=uuid.uuid4(), email="admin@test.com", full_name="Admin User", password_hash="pass", role_id=role_admin.id
    )
    scm_user = User(
        id=uuid.uuid4(), email="scm@test.com", full_name="SCM User", password_hash="pass", role_id=role_scm.id
    )
    io_user = User(
        id=uuid.uuid4(), email="io@test.com", full_name="IO User", password_hash="pass", role_id=role_io.id
    )
    session.add_all([admin_user, scm_user, io_user])

    # Seed facilities
    facility_source = Facility(id=uuid.uuid4(), code="FAC-SRC", name="Source Facility")
    facility_dest = Facility(id=uuid.uuid4(), code="FAC-DST", name="Destination Facility")
    session.add_all([facility_source, facility_dest])

    # Seed medicine
    medicine = Medicine(id=uuid.uuid4(), code="MED-001", generic_name="Amoxicillin 500mg", unit_of_measure="capsule")
    session.add(medicine)
    session.flush()

    # Seed policies
    policy_src = FacilityMedicinePolicy(
        facility_id=facility_source.id, medicine_id=medicine.id, safety_stock=Decimal("100.00")
    )
    policy_dst = FacilityMedicinePolicy(
        facility_id=facility_dest.id, medicine_id=medicine.id, safety_stock=Decimal("100.00")
    )
    session.add_all([policy_src, policy_dst])

    # Seed initial inventory balances
    bal_src = InventoryBalance(
        facility_id=facility_source.id, medicine_id=medicine.id, quantity_on_hand=Decimal("1000.00")
    )
    bal_dst = InventoryBalance(
        facility_id=facility_dest.id, medicine_id=medicine.id, quantity_on_hand=Decimal("50.00")
    )
    session.add_all([bal_src, bal_dst])

    # Seed batch at source
    batch_src = Batch(
        facility_id=facility_source.id,
        medicine_id=medicine.id,
        batch_number="BATCH-2026-A",
        expiry_date=date(2027, 12, 31),
        quantity=Decimal("500.00"),
    )
    session.add(batch_src)
    session.flush()

    session.commit()
    yield session
    session.close()


@pytest.fixture
def sample_approved_recommendation(db_session: Session):
    scm_user = db_session.scalar(select(User).where(User.email == "scm@test.com"))
    facility_src = db_session.scalar(select(Facility).where(Facility.code == "FAC-SRC"))
    facility_dst = db_session.scalar(select(Facility).where(Facility.code == "FAC-DST"))
    medicine = db_session.scalar(select(Medicine).where(Medicine.code == "MED-001"))

    now = datetime.now(timezone.utc)
    rec = RedistributionRecommendation(
        source_facility_id=facility_src.id,
        destination_facility_id=facility_dst.id,
        medicine_id=medicine.id,
        status=RedistributionRecommendationStatus.APPROVED,
        planning_horizon_days=14,
        source_surplus_units=Decimal("500.00"),
        destination_shortage_units=Decimal("200.00"),
        recommended_quantity=Decimal("200.00"),
        source_inventory_before=Decimal("1000.00"),
        destination_inventory_before=Decimal("50.00"),
        source_safety_stock=Decimal("100.00"),
        destination_safety_stock=Decimal("100.00"),
        source_projected_end_inventory=Decimal("500.00"),
        destination_projected_end_inventory=Decimal("250.00"),
        constraint_results={"recommendation_feasible": True},
        expires_at=now + timedelta(hours=24),
        created_by=scm_user.id,
        reviewed_by=scm_user.id,
        reviewed_at=now,
    )
    db_session.add(rec)
    db_session.commit()
    db_session.refresh(rec)
    return rec


# 1. APPROVED -> IN_TRANSIT -> COMPLETED Happy Path
def test_transfer_happy_path_state_machine(db_session: Session, sample_approved_recommendation):
    scm_user = db_session.scalar(select(User).where(User.email == "scm@test.com"))
    batch = db_session.scalar(select(Batch).where(Batch.batch_number == "BATCH-2026-A"))

    # Create transfer
    payload = TransferCreate(
        recommendation_id=sample_approved_recommendation.id,
        batch_id=batch.id,
        quantity=Decimal("150.00"),
    )
    transfer = create_transfer(db_session, payload, scm_user)
    assert transfer.status == RedistributionTransferStatus.APPROVED
    assert transfer.quantity == Decimal("150.00")

    # Dispatch transfer
    dispatched = dispatch_transfer(db_session, transfer.id, scm_user)
    assert dispatched.status == RedistributionTransferStatus.IN_TRANSIT
    assert dispatched.dispatched_at is not None

    # Verify source stock decreased
    src_bal = db_session.scalar(
        select(InventoryBalance).where(
            InventoryBalance.facility_id == sample_approved_recommendation.source_facility_id,
            InventoryBalance.medicine_id == sample_approved_recommendation.medicine_id,
        )
    )
    assert src_bal.quantity_on_hand == Decimal("850.00")

    # Complete transfer
    completed = complete_transfer(db_session, transfer.id, scm_user)
    assert completed.status == RedistributionTransferStatus.COMPLETED
    assert completed.received_at is not None

    # Verify destination stock increased
    dst_bal = db_session.scalar(
        select(InventoryBalance).where(
            InventoryBalance.facility_id == sample_approved_recommendation.destination_facility_id,
            InventoryBalance.medicine_id == sample_approved_recommendation.medicine_id,
        )
    )
    assert dst_bal.quantity_on_hand == Decimal("200.00")


# 2. APPROVED -> CANCELLED
def test_transfer_cancellation_from_approved(db_session: Session, sample_approved_recommendation):
    scm_user = db_session.scalar(select(User).where(User.email == "scm@test.com"))
    payload = TransferCreate(
        recommendation_id=sample_approved_recommendation.id,
        quantity=Decimal("100.00"),
    )
    transfer = create_transfer(db_session, payload, scm_user)
    assert transfer.status == RedistributionTransferStatus.APPROVED

    cancelled = cancel_transfer(db_session, transfer.id, scm_user, reason="Stock re-allocated locally")
    assert cancelled.status == RedistributionTransferStatus.CANCELLED
    assert cancelled.cancellation_reason == "Stock re-allocated locally"


# 3. IN_TRANSIT -> CANCELLED is Rejected
def test_in_transit_cancellation_is_rejected(db_session: Session, sample_approved_recommendation):
    scm_user = db_session.scalar(select(User).where(User.email == "scm@test.com"))
    payload = TransferCreate(
        recommendation_id=sample_approved_recommendation.id,
        quantity=Decimal("100.00"),
    )
    transfer = create_transfer(db_session, payload, scm_user)
    dispatch_transfer(db_session, transfer.id, scm_user)

    with pytest.raises(HTTPException) as exc_info:
        cancel_transfer(db_session, transfer.id, scm_user, reason="Attempt cancellation while in transit")
    assert exc_info.value.status_code == 409
    assert "IN_TRANSIT" in exc_info.value.detail


# 4. Dispatch creates exactly one TRANSFER_OUT
def test_dispatch_creates_exactly_one_transfer_out(db_session: Session, sample_approved_recommendation):
    scm_user = db_session.scalar(select(User).where(User.email == "scm@test.com"))
    payload = TransferCreate(
        recommendation_id=sample_approved_recommendation.id,
        quantity=Decimal("100.00"),
    )
    transfer = create_transfer(db_session, payload, scm_user)
    dispatch_transfer(db_session, transfer.id, scm_user)

    txs = db_session.scalars(
        select(InventoryTransaction).where(
            InventoryTransaction.reference_number == f"TRANSFER-OUT-{transfer.id}"
        )
    ).all()
    assert len(txs) == 1
    assert txs[0].transaction_type == InventoryTransactionType.TRANSFER_OUT
    assert txs[0].quantity == Decimal("100.00")


# 5. Completion creates exactly one TRANSFER_IN
def test_completion_creates_exactly_one_transfer_in(db_session: Session, sample_approved_recommendation):
    scm_user = db_session.scalar(select(User).where(User.email == "scm@test.com"))
    payload = TransferCreate(
        recommendation_id=sample_approved_recommendation.id,
        quantity=Decimal("100.00"),
    )
    transfer = create_transfer(db_session, payload, scm_user)
    dispatch_transfer(db_session, transfer.id, scm_user)
    complete_transfer(db_session, transfer.id, scm_user)

    txs = db_session.scalars(
        select(InventoryTransaction).where(
            InventoryTransaction.reference_number == f"TRANSFER-IN-{transfer.id}"
        )
    ).all()
    assert len(txs) == 1
    assert txs[0].transaction_type == InventoryTransactionType.TRANSFER_IN
    assert txs[0].quantity == Decimal("100.00")


# 6. Repeated dispatch is idempotent and does not duplicate inventory movements
def test_repeated_dispatch_is_idempotent(db_session: Session, sample_approved_recommendation):
    scm_user = db_session.scalar(select(User).where(User.email == "scm@test.com"))
    payload = TransferCreate(
        recommendation_id=sample_approved_recommendation.id,
        quantity=Decimal("100.00"),
    )
    transfer = create_transfer(db_session, payload, scm_user)
    first_dispatch = dispatch_transfer(db_session, transfer.id, scm_user)
    second_dispatch = dispatch_transfer(db_session, transfer.id, scm_user)

    assert first_dispatch.id == second_dispatch.id
    assert second_dispatch.status == RedistributionTransferStatus.IN_TRANSIT

    # Ensure source stock decreased only once
    src_bal = db_session.scalar(
        select(InventoryBalance).where(
            InventoryBalance.facility_id == sample_approved_recommendation.source_facility_id,
            InventoryBalance.medicine_id == sample_approved_recommendation.medicine_id,
        )
    )
    assert src_bal.quantity_on_hand == Decimal("900.00")

    txs = db_session.scalars(
        select(InventoryTransaction).where(
            InventoryTransaction.reference_number == f"TRANSFER-OUT-{transfer.id}"
        )
    ).all()
    assert len(txs) == 1


# 7. Repeated completion is idempotent and does not duplicate inventory movements
def test_repeated_completion_is_idempotent(db_session: Session, sample_approved_recommendation):
    scm_user = db_session.scalar(select(User).where(User.email == "scm@test.com"))
    payload = TransferCreate(
        recommendation_id=sample_approved_recommendation.id,
        quantity=Decimal("100.00"),
    )
    transfer = create_transfer(db_session, payload, scm_user)
    dispatch_transfer(db_session, transfer.id, scm_user)
    first_comp = complete_transfer(db_session, transfer.id, scm_user)
    second_comp = complete_transfer(db_session, transfer.id, scm_user)

    assert first_comp.id == second_comp.id
    assert second_comp.status == RedistributionTransferStatus.COMPLETED

    dst_bal = db_session.scalar(
        select(InventoryBalance).where(
            InventoryBalance.facility_id == sample_approved_recommendation.destination_facility_id,
            InventoryBalance.medicine_id == sample_approved_recommendation.medicine_id,
        )
    )
    assert dst_bal.quantity_on_hand == Decimal("150.00")

    txs = db_session.scalars(
        select(InventoryTransaction).where(
            InventoryTransaction.reference_number == f"TRANSFER-IN-{transfer.id}"
        )
    ).all()
    assert len(txs) == 1


# 8. Insufficient source stock causes dispatch failure with rollback
def test_insufficient_stock_causes_dispatch_failure(db_session: Session, sample_approved_recommendation):
    scm_user = db_session.scalar(select(User).where(User.email == "scm@test.com"))
    payload = TransferCreate(
        recommendation_id=sample_approved_recommendation.id,
        quantity=Decimal("200.00"),
    )
    transfer = create_transfer(db_session, payload, scm_user)

    # Artificially drop source inventory below transfer quantity
    src_bal = db_session.scalar(
        select(InventoryBalance).where(
            InventoryBalance.facility_id == sample_approved_recommendation.source_facility_id,
            InventoryBalance.medicine_id == sample_approved_recommendation.medicine_id,
        )
    )
    src_bal.quantity_on_hand = Decimal("50.00")
    db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        dispatch_transfer(db_session, transfer.id, scm_user)
    assert exc_info.value.status_code == 409
    assert "Insufficient source inventory" in exc_info.value.detail

    # Verify status remains APPROVED and stock remains 50.00
    db_session.refresh(transfer)
    assert transfer.status == RedistributionTransferStatus.APPROVED
    assert src_bal.quantity_on_hand == Decimal("50.00")


# 9. Failed completion on invalid status causes no partial database changes
def test_failed_completion_invalid_status(db_session: Session, sample_approved_recommendation):
    scm_user = db_session.scalar(select(User).where(User.email == "scm@test.com"))
    payload = TransferCreate(
        recommendation_id=sample_approved_recommendation.id,
        quantity=Decimal("100.00"),
    )
    transfer = create_transfer(db_session, payload, scm_user)

    with pytest.raises(HTTPException) as exc_info:
        complete_transfer(db_session, transfer.id, scm_user)
    assert exc_info.value.status_code == 409

    # Destination stock unchanged
    dst_bal = db_session.scalar(
        select(InventoryBalance).where(
            InventoryBalance.facility_id == sample_approved_recommendation.destination_facility_id,
            InventoryBalance.medicine_id == sample_approved_recommendation.medicine_id,
        )
    )
    assert dst_bal.quantity_on_hand == Decimal("50.00")


# 10. Stale / Expired recommendation cannot be created or dispatched
def test_expired_recommendation_rejected(db_session: Session, sample_approved_recommendation):
    scm_user = db_session.scalar(select(User).where(User.email == "scm@test.com"))
    
    # Expire recommendation
    sample_approved_recommendation.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
    db_session.commit()

    payload = TransferCreate(
        recommendation_id=sample_approved_recommendation.id,
        quantity=Decimal("100.00"),
    )
    with pytest.raises(HTTPException) as exc_info:
        create_transfer(db_session, payload, scm_user)
    assert exc_info.value.status_code == 409
    assert "expired" in exc_info.value.detail


# 11. Unauthorized user role checks (service/routing contract verification)
def test_unauthorized_user_role_handling(db_session: Session, sample_approved_recommendation):
    from app.api.routes.transfers import create_transfer_endpoint, dispatch_transfer_endpoint
    from app.api.deps import require_roles
    
    # Check that route dependency enforces roles
    dep = require_roles(RoleCode.ADMINISTRATOR, RoleCode.SUPPLY_CHAIN_MANAGER)
    io_user = db_session.scalar(select(User).where(User.email == "io@test.com"))
    
    with pytest.raises(HTTPException) as exc_info:
        dep(current_user=io_user)
    assert exc_info.value.status_code == 403


# 12. Audit records are created for required business events
def test_audit_log_events_generated(db_session: Session, sample_approved_recommendation):
    scm_user = db_session.scalar(select(User).where(User.email == "scm@test.com"))
    
    # Approve recommendation audit check
    now = datetime.now(timezone.utc)
    rec_pending = RedistributionRecommendation(
        source_facility_id=sample_approved_recommendation.source_facility_id,
        destination_facility_id=sample_approved_recommendation.destination_facility_id,
        medicine_id=sample_approved_recommendation.medicine_id,
        status=RedistributionRecommendationStatus.PENDING_REVIEW,
        planning_horizon_days=14,
        source_surplus_units=Decimal("500.00"),
        destination_shortage_units=Decimal("200.00"),
        recommended_quantity=Decimal("200.00"),
        source_inventory_before=Decimal("1000.00"),
        destination_inventory_before=Decimal("50.00"),
        source_safety_stock=Decimal("100.00"),
        destination_safety_stock=Decimal("100.00"),
        source_projected_end_inventory=Decimal("500.00"),
        destination_projected_end_inventory=Decimal("250.00"),
        constraint_results={"recommendation_feasible": True},
        expires_at=now + timedelta(hours=24),
        created_by=scm_user.id,
    )
    db_session.add(rec_pending)
    db_session.commit()

    decide_recommendation(db_session, rec_pending.id, approved=True, reviewer_id=scm_user.id, note="Approved in test")

    # Transfer lifecycle audit check
    payload = TransferCreate(recommendation_id=rec_pending.id, quantity=Decimal("100.00"))
    transfer = create_transfer(db_session, payload, scm_user)
    dispatch_transfer(db_session, transfer.id, scm_user)
    complete_transfer(db_session, transfer.id, scm_user)

    audit_actions = db_session.scalars(select(AuditLog.action)).all()
    assert "RECOMMENDATION_APPROVED" in audit_actions
    assert "TRANSFER_CREATED" in audit_actions
    assert "TRANSFER_DISPATCHED" in audit_actions
    assert "INVENTORY_TRANSFER_OUT" in audit_actions
    assert "TRANSFER_COMPLETED" in audit_actions
    assert "INVENTORY_TRANSFER_IN" in audit_actions
