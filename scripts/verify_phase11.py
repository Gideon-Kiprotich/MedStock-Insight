"""Reconcile and compare two explicitly supplied disposable local demonstration databases."""
import hashlib
import json
import os
import sys
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi.encoders import jsonable_encoder
from sqlalchemy import create_engine, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.models.core import (
    Facility,
    InventoryBalance,
    InventoryTransaction,
    InventoryTransactionType,
    Medicine,
    RedistributionTransfer,
    RiskAssessment,
    User,
)
from app.services.analytics import aggregate_rows, evaluate_network
from app.services.experiments import ScenarioParameters, create_scenario
from app.services.forecasting import ForecastModelCode, evaluate_series


def digest(value):
    return hashlib.sha256(json.dumps(jsonable_encoder(value), sort_keys=True).encode()).hexdigest()


def evidence(url):
    parsed = make_url(url)
    if parsed.host not in {'localhost','127.0.0.1'} or not parsed.database.startswith('phase11_'):
        raise ValueError('Use explicitly disposable local phase11_ databases')
    engine = create_engine(url)
    with Session(engine) as db:
        facilities = {f.id:f for f in db.scalars(select(Facility))}
        medicines = {m.id:m for m in db.scalars(select(Medicine))}
        reference = []
        for rows in [facilities, medicines]:
            for entity in sorted(rows.values(), key=lambda x:x.code):
                reference.append({c.name:getattr(entity,c.name) for c in entity.__table__.columns
                                  if c.name not in {'id','created_at','updated_at'}})
                assert entity.source_url and entity.source_name and entity.source_record_id
                assert entity.retrieved_at and entity.verification_status == 'SOURCE_VERIFIED'
        assert len(facilities)==9 and len(medicines)==51
        assert not any(f.code.startswith('FAC-') for f in facilities.values())
        assert not any(m.code.startswith('MED-') for m in medicines.values())
        for user in db.scalars(select(User)):
            assert user.is_demo_user and user.email.endswith('@medstock.example') and user.facility_id
        totals = defaultdict(Decimal)
        transactions = []
        for tx in db.scalars(select(InventoryTransaction).order_by(InventoryTransaction.transaction_date)):
            sign = 1 if tx.transaction_type in {InventoryTransactionType.RECEIPT,InventoryTransactionType.ADJUSTMENT_IN,InventoryTransactionType.TRANSFER_IN} else -1
            totals[(tx.facility_id,tx.medicine_id)] += sign*tx.quantity
            transactions.append((facilities[tx.facility_id].code,medicines[tx.medicine_id].code,
                                 str(tx.transaction_date),tx.transaction_type.value,str(tx.quantity)))
        balances = {(b.facility_id,b.medicine_id):b.quantity_on_hand for b in db.scalars(select(InventoryBalance))}
        assert totals == balances
        assert len([t for t in transactions if t[3]=='CONSUMPTION'])==181040
        risks=sorted((facilities[r.facility_id].code,medicines[r.medicine_id].code,r.risk_level.value,
                      r.days_to_breach,str(r.projected_shortage_units)) for r in db.scalars(select(RiskAssessment)))
        transfers=sorted((facilities[t.source_facility_id].code,facilities[t.destination_facility_id].code,
                          medicines[t.medicine_id].code,str(t.quantity),t.status.value)
                         for t in db.scalars(select(RedistributionTransfer)))
        evaluation=evaluate_network(db)
        # Recompute every measured metric from the stored temporal inputs, then pool independently.
        computed=[]
        for item in evaluation['context']['inputs']:
            from datetime import date
            for model in ForecastModelCode:
                measured=evaluate_series(item['values'],model,date.fromisoformat(item['start']))
                if measured:
                    errors=[a-p for a,p in zip(measured.actual,measured.predicted)]
                    computed.append({'model':model.value,'status':'MEASURED','observations':len(errors),
                        'absolute_error':sum(abs(x) for x in errors),'squared_error':sum(x*x for x in errors),
                        'actual_total':sum(abs(x) for x in measured.actual)})
        assert aggregate_rows(computed)==evaluation['overall']
        destination=next(f for f in facilities.values() if f.code=='13156')
        medicine=next(m for m in medicines.values() if m.generic_name=='Paracetamol' and m.strength=='500 mg')
        scenario=create_scenario(db,ScenarioParameters(facility_id=destination.id,medicine_id=medicine.id,
                            demand_adjustment_pct=30,inventory_adjustment_pct=-30))
        assert balances == {(b.facility_id,b.medicine_id):b.quantity_on_hand for b in db.scalars(select(InventoryBalance))}
        result={'reference':digest(reference),'ledger':digest(sorted(transactions)),
                'controlled_risks':digest(risks),'controlled_transfers':digest(transfers),
                'evaluation':evaluation['overall'],'scenario':scenario['reproducibility_fingerprint'],
                'observations':181040,'series':evaluation['series_count'],'reconciled_balances':len(balances)}
    engine.dispose()
    return result


def main():
    first=evidence(os.environ['DATABASE_URL'])
    print('First database reconciled; all stored evaluation metrics reproduced.',flush=True)
    second=evidence(os.environ['MEDSTOCK_REPRO_COMPARE_URL'])
    assert first==second,(first,second)
    output=Path('/tmp/medstock-phase11-reproducibility.json')
    output.write_text(json.dumps({'passed':True,'comparison':first},indent=2))
    print(json.dumps({'passed':True,'comparison':first},indent=2))


if __name__=='__main__':
    main()
