from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import uuid

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.models.core import (
    Batch,
    Facility,
    FacilityMedicinePolicy,
    ForecastRun,
    ForecastRunStatus,
    InventoryBalance,
    Medicine,
    RedistributionRecommendation,
    RedistributionRecommendationStatus,
    RedistributionTransfer,
    RedistributionTransferStatus,
    RiskAssessment,
    RiskLevel,
    Role,
    RoleCode,
    User,
)
from app.services.dashboard import get_dashboard_read_model


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
    session.add(admin_user)

    # Seed 2 facilities
    fac1 = Facility(id=uuid.uuid4(), code="FAC-A", name="Facility Alpha")
    fac2 = Facility(id=uuid.uuid4(), code="FAC-B", name="Facility Beta")
    session.add_all([fac1, fac2])

    # Seed 2 medicines
    med1 = Medicine(id=uuid.uuid4(), code="MED-01", generic_name="Paracetamol 500mg")
    med2 = Medicine(id=uuid.uuid4(), code="MED-02", generic_name="Amoxicillin 250mg")
    session.add_all([med1, med2])
    session.flush()

    # Seed inventory balances: fac1 med1 = 0 (stockout), fac2 med1 = 500
    bal1 = InventoryBalance(facility_id=fac1.id, medicine_id=med1.id, quantity_on_hand=Decimal("0.00"))
    bal2 = InventoryBalance(facility_id=fac2.id, medicine_id=med1.id, quantity_on_hand=Decimal("500.00"))
    session.add_all([bal1, bal2])

    # Dummy forecast run
    fr = ForecastRun(
        id=uuid.uuid4(),
        facility_id=fac1.id,
        medicine_id=med1.id,
        model_version_id=uuid.uuid4(),
        forecast_start_date=date.today(),
        horizon_days=14,
        training_start_date=date.today() - timedelta(days=30),
        training_end_date=date.today(),
        data_points_used=30,
        status=ForecastRunStatus.COMPLETED,
    )
    session.add(fr)
    session.flush()

    # Seed risk assessment for fac1 (CRITICAL) & fac2 (LOW)
    ra1 = RiskAssessment(
        facility_id=fac1.id,
        medicine_id=med1.id,
        forecast_run_id=fr.id,
        risk_level=RiskLevel.CRITICAL,
        currently_out_of_stock=True,
        days_to_breach=0,
        inventory_on_hand=Decimal("0.00"),
        safety_stock=Decimal("100.00"),
        reorder_point=Decimal("200.00"),
        forecast_horizon_days=14,
        calculation_version="risk-1.0",
    )
    ra2 = RiskAssessment(
        facility_id=fac2.id,
        medicine_id=med1.id,
        forecast_run_id=fr.id,
        risk_level=RiskLevel.LOW,
        currently_out_of_stock=False,
        days_to_breach=15,
        inventory_on_hand=Decimal("500.00"),
        safety_stock=Decimal("100.00"),
        reorder_point=Decimal("200.00"),
        forecast_horizon_days=14,
        calculation_version="risk-1.0",
    )
    session.add_all([ra1, ra2])

    # Seed recommendation
    now = datetime.now(timezone.utc)
    rec = RedistributionRecommendation(
        source_facility_id=fac2.id,
        destination_facility_id=fac1.id,
        medicine_id=med1.id,
        status=RedistributionRecommendationStatus.PENDING_REVIEW,
        planning_horizon_days=14,
        source_surplus_units=Decimal("400.00"),
        destination_shortage_units=Decimal("200.00"),
        recommended_quantity=Decimal("200.00"),
        source_inventory_before=Decimal("500.00"),
        destination_inventory_before=Decimal("0.00"),
        source_safety_stock=Decimal("100.00"),
        destination_safety_stock=Decimal("100.00"),
        source_projected_end_inventory=Decimal("300.00"),
        destination_projected_end_inventory=Decimal("200.00"),
        constraint_results={"recommendation_feasible": True},
        expires_at=now + timedelta(hours=24),
        created_by=admin_user.id,
    )
    session.add(rec)
    session.flush()

    # Seed transfer
    tr = RedistributionTransfer(
        recommendation_id=rec.id,
        source_facility_id=fac2.id,
        destination_facility_id=fac1.id,
        medicine_id=med1.id,
        quantity=Decimal("200.00"),
        status=RedistributionTransferStatus.IN_TRANSIT,
        approved_by=admin_user.id,
        approved_at=now,
        dispatched_by=admin_user.id,
        dispatched_at=now,
    )
    session.add(tr)

    session.commit()
    yield session
    session.close()


def test_dashboard_read_model_summary(db_session: Session):
    model = get_dashboard_read_model(db_session)
    assert model.summary.facilities_count == 2
    assert model.summary.medicines_tracked == 2
    assert model.summary.active_stockouts == 1
    assert model.summary.critical_risk_count == 1
    assert model.summary.low_risk_count == 1
    assert model.summary.pending_redistribution_count == 1
    assert model.summary.in_transit_transfer_count == 1


def test_dashboard_risk_worklist_ordering(db_session: Session):
    model = get_dashboard_read_model(db_session)
    assert len(model.risk_worklist) == 2
    assert model.risk_worklist[0].risk_level == RiskLevel.CRITICAL
    assert model.risk_worklist[0].facility_code == "FAC-A"
    assert model.risk_worklist[0].data_classification == "PREDICTED"


def test_dashboard_redistribution_queue(db_session: Session):
    model = get_dashboard_read_model(db_session)
    assert len(model.redistribution_queue) == 1
    item = model.redistribution_queue[0]
    assert item.status == RedistributionRecommendationStatus.PENDING_REVIEW
    assert item.recommended_quantity == Decimal("200.00")
    assert item.data_classification == "RECOMMENDED"


def test_dashboard_recent_transfers(db_session: Session):
    model = get_dashboard_read_model(db_session)
    assert len(model.recent_transfers) == 1
    tr = model.recent_transfers[0]
    assert tr.status == RedistributionTransferStatus.IN_TRANSIT
    assert tr.data_classification == "CONFIRMED"


def test_dashboard_facility_summaries(db_session: Session):
    model = get_dashboard_read_model(db_session)
    assert len(model.facility_summaries) == 2
    fac_a = next(f for f in model.facility_summaries if f.facility_code == "FAC-A")
    assert fac_a.active_stockouts == 1
    assert fac_a.critical_high_risk_count == 1


def test_dashboard_filtering_by_facility(db_session: Session):
    fac1 = db_session.scalar(select(Facility).where(Facility.code == "FAC-A"))
    model = get_dashboard_read_model(db_session, facility_id=fac1.id)
    assert model.summary.facilities_count == 1
    assert len(model.risk_worklist) == 1
    assert model.risk_worklist[0].facility_code == "FAC-A"


def test_dashboard_empty_data_handling():
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    empty_session = testing_session_local()

    model = get_dashboard_read_model(empty_session)
    assert model.summary.facilities_count == 0
    assert model.summary.medicines_tracked == 0
    assert model.summary.active_stockouts == 0
    assert len(model.risk_worklist) == 0
    assert len(model.redistribution_queue) == 0
    assert len(model.recent_transfers) == 0
    assert len(model.facility_summaries) == 0
    empty_session.close()


def test_dashboard_queries_are_read_only(db_session: Session):
    # Capture initial database state
    bal_before = db_session.scalars(select(InventoryBalance)).all()
    stock_before = {b.id: b.quantity_on_hand for b in bal_before}

    # Execute dashboard read model
    _ = get_dashboard_read_model(db_session)

    # Confirm no state changes
    bal_after = db_session.scalars(select(InventoryBalance)).all()
    stock_after = {b.id: b.quantity_on_hand for b in bal_after}

    assert stock_before == stock_after
