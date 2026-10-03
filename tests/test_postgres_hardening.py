"""Real PostgreSQL stale-session races; opt in with a disposable local test URL."""
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from secrets import token_urlsafe
from threading import Barrier
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.core import (
    Facility,
    FacilityMedicinePolicy,
    InventoryBalance,
    InventoryTransaction,
    Medicine,
    RedistributionRecommendation,
    RedistributionRecommendationStatus,
    RedistributionTransfer,
    Role,
    RoleCode,
    User,
)
from app.schemas.transfers import TransferCreate
from app.services.transfer import complete_transfer, create_transfer, dispatch_transfer


@pytest.fixture
def pg():
    url = os.environ.get('MEDSTOCK_POSTGRES_TEST_URL')
    if not url:
        pytest.skip('Requires explicitly supplied disposable PostgreSQL URL')
    parsed = make_url(url)
    assert parsed.host in {'127.0.0.1','localhost'} and parsed.database.startswith('phase11_')
    admin = create_engine(url)
    schema = 'test_'+uuid4().hex
    with admin.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_engine(url, connect_args={'options':f'-csearch_path={schema}'})
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        source, destination = Facility(code='SRC',name='Synthetic source'), Facility(code='DST',name='Synthetic destination')
        medicine = Medicine(code='PARA',generic_name='Paracetamol')
        actor = User(email='manager@test.example',full_name='Synthetic manager',password_hash=token_urlsafe(24),
                     role=Role(code=RoleCode.SUPPLY_CHAIN_MANAGER,name='Manager'))
        db.add_all([source,destination,medicine,actor])
        db.flush()
        db.add_all([InventoryBalance(facility_id=source.id,medicine_id=medicine.id,quantity_on_hand=100),
                    InventoryBalance(facility_id=destination.id,medicine_id=medicine.id,quantity_on_hand=0),
                    FacilityMedicinePolicy(facility_id=source.id,medicine_id=medicine.id,safety_stock=10,reorder_point=20,lead_time_days=7)])
        rec = RedistributionRecommendation(source_facility_id=source.id,destination_facility_id=destination.id,
            medicine_id=medicine.id,status=RedistributionRecommendationStatus.APPROVED,
            planning_horizon_days=14,source_surplus_units=80,destination_shortage_units=20,recommended_quantity=20,
            source_inventory_before=100,destination_inventory_before=0,source_safety_stock=10,destination_safety_stock=10,
            source_projected_end_inventory=80,destination_projected_end_inventory=-20,constraint_results={},
            expires_at=datetime.now(timezone.utc)+timedelta(hours=24),created_by=actor.id)
        db.add(rec)
        db.commit()
        yield engine, rec.id, actor.id
    engine.dispose()
    with admin.begin() as connection:
        connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
    admin.dispose()


@pytest.mark.parametrize('operation',['dispatch','complete'])
def test_stale_transfer_objects_cannot_duplicate_movements(pg, operation):
    engine, rec_id, actor_id = pg
    with Session(engine) as db:
        transfer = create_transfer(db,TransferCreate(recommendation_id=rec_id,quantity=5),db.get(User,actor_id))
        transfer_id = transfer.id
        if operation == 'complete':
            dispatch_transfer(db,transfer_id,db.get(User,actor_id))
    barrier = Barrier(2)
    def worker(_):
        with Session(engine) as db:
            # Deliberately cache the same old transfer state before either caller acquires its lock.
            stale = db.get(RedistributionTransfer,transfer_id)
            actor = db.get(User,actor_id)
            barrier.wait(timeout=10)
            result = (dispatch_transfer if operation=='dispatch' else complete_transfer)(db,transfer_id,actor)
            assert stale is result
            return result.status.value
    with ThreadPoolExecutor(max_workers=2) as pool:
        result = list(pool.map(worker,range(2)))
    assert result == (['IN_TRANSIT']*2 if operation=='dispatch' else ['COMPLETED']*2)
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(InventoryTransaction).where(
            InventoryTransaction.reference_number==f"TRANSFER-{'OUT' if operation=='dispatch' else 'IN'}-{transfer_id}")) == 1
        quantities = sorted(db.scalars(select(InventoryBalance.quantity_on_hand)).all())
        assert quantities == ([Decimal(0),Decimal(95)] if operation=='dispatch' else [Decimal(5),Decimal(95)])


def test_concurrent_creations_reserve_recommendation_once(pg):
    from fastapi import HTTPException
    engine, rec_id, actor_id = pg
    barrier = Barrier(2)
    def worker(_):
        with Session(engine) as db:
            db.get(RedistributionRecommendation,rec_id)
            actor=db.get(User,actor_id)
            barrier.wait(timeout=10)
            try:
                create_transfer(db,TransferCreate(recommendation_id=rec_id,quantity=5),actor)
                return 201
            except HTTPException as exc:
                db.rollback()
                return exc.status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(worker,range(2))) == [201,409]
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(RedistributionTransfer)) == 1
        assert db.scalar(select(func.count()).select_from(InventoryTransaction)) == 0
