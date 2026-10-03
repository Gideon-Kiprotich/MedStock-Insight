"""Security boundaries exercised through HTTP and meaningful analytical regressions."""
from datetime import date
from secrets import token_urlsafe
from uuid import uuid4

import jwt
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.config import Settings, get_settings
from app.core.security import create_access_token, hash_password
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.core import (
    AuditLog,
    Facility,
    ForecastModelCode,
    InventoryBalance,
    Medicine,
    Role,
    RoleCode,
    User,
)
from app.services.experiments import reproducibility_fingerprint
from app.services.forecasting import _rf_features, evaluate_series


@pytest.fixture
def api_fixture():
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        facility = Facility(code='TEST-A', name='Synthetic test facility')
        other = Facility(code='TEST-B', name='Other synthetic test facility')
        medicine = Medicine(code='TEST-M', generic_name='Paracetamol')
        db.add_all([facility, other, medicine])
        db.flush()
        actors = {}
        for code in RoleCode:
            role = Role(code=code, name=code.value)
            user = User(email=code.value.lower()+'@test.example', full_name='Synthetic test user',
                        role=role, facility_id=facility.id, password_hash=hash_password(token_urlsafe(18)),
                        is_demo_user=True, is_active=True)
            db.add(user)
            actors[code] = user
        db.commit()
        app.dependency_overrides[get_db] = lambda: db
        with TestClient(app, raise_server_exceptions=False) as client:
            yield client, db, actors, facility, other, medicine
        app.dependency_overrides.clear()
    engine.dispose()


def headers(user, claimed_role=None):
    return {'Authorization': 'Bearer '+create_access_token(str(user.id), claimed_role or user.role.code.value)}


def test_configuration_fails_closed_for_debug_placeholder_and_wildcard():
    for invalid in [{'jwt_secret_key':'replace-with-a-long-random-secret'}, {'cors_origins':'*'},
                    {'cors_origins':'https://user:password@example.org'}, {'jwt_algorithm':'none'},
                    {'environment':'production','debug':True}, {'access_token_expire_minutes':0}]:
        with pytest.raises(ValidationError):
            Settings(_env_file=None, **invalid)
    assert not Settings(_env_file=None, debug=False).debug


def test_anonymous_routes_and_forged_role_do_not_bypass_database_rbac(api_fixture):
    client, _, actors, _, _, _ = api_fixture
    for path in ['/inventory','/audit','/users/demo','/scenarios/'+str(uuid4()), '/decision-analytics']:
        assert client.get('/api/v1'+path).status_code == 401
    officer = actors[RoleCode.INVENTORY_OFFICER]
    assert client.get('/api/v1/users/demo', headers=headers(officer,'ADMINISTRATOR')).status_code == 403
    assert client.post('/api/v1/forecast-evaluation/experiments', json={}, headers=headers(officer)).status_code == 403
    manager = actors[RoleCode.SUPPLY_CHAIN_MANAGER]
    assert client.get('/api/v1/users/demo', headers=headers(manager)).status_code == 403
    response = client.get('/api/v1/users/demo', headers=headers(actors[RoleCode.ADMINISTRATOR]))
    assert response.status_code == 200 and all('password_hash' not in r for r in response.json())


def test_missing_expired_invalid_and_inactive_tokens_are_rejected(api_fixture):
    client, db, actors, _, _, _ = api_fixture
    user = actors[RoleCode.ADMINISTRATOR]
    settings = get_settings()
    no_expiry = jwt.encode({'sub':str(user.id)}, settings.jwt_secret_key, algorithm='HS256')
    expired = jwt.encode({'sub':str(user.id), 'exp':1}, settings.jwt_secret_key, algorithm='HS256')
    no_subject = jwt.encode({'exp':4102444800}, settings.jwt_secret_key, algorithm='HS256')
    for token in [no_expiry, expired, no_subject, 'invalid-token']:
        assert client.get('/api/v1/inventory', headers={'Authorization':'Bearer '+token}).status_code == 401
    valid = headers(user)
    user.is_active = False
    db.commit()
    assert client.get('/api/v1/inventory', headers=valid).status_code == 401


def test_inventory_scope_transfer_bypass_and_audit(api_fixture):
    client, db, actors, facility, other, medicine = api_fixture
    payload = {'facility_id':str(other.id), 'medicine_id':str(medicine.id), 'transaction_type':'RECEIPT',
               'quantity':5, 'transaction_date':str(date.today())}
    officer = headers(actors[RoleCode.INVENTORY_OFFICER])
    assert client.post('/api/v1/inventory/transactions', json=payload, headers=officer).status_code == 403
    assert client.post('/api/v1/inventory/transactions', json=payload,
                       headers=headers(actors[RoleCode.SUPPLY_CHAIN_MANAGER])).status_code == 403
    payload['facility_id'] = str(facility.id)
    for kind in ['TRANSFER_IN','TRANSFER_OUT']:
        payload['transaction_type'] = kind
        assert client.post('/api/v1/inventory/transactions', json=payload, headers=officer).status_code == 422
    assert db.scalars(select(InventoryBalance)).all() == []
    payload['transaction_type'] = 'RECEIPT'
    response = client.post('/api/v1/inventory/transactions', json=payload, headers=officer)
    assert response.status_code == 201
    assert db.scalar(select(InventoryBalance)).quantity_on_hand == 5
    assert db.scalar(select(AuditLog)).action == 'INVENTORY_TRANSACTION_CREATED'


def test_features_and_all_holdout_predictions_exclude_current_and_future_targets():
    values = [float(4+i%8) for i in range(100)]
    assert _rf_features(values, 70) == _rf_features(values[:70]+[99999.0]*30, 70)
    for model in ForecastModelCode:
        baseline = evaluate_series(values, model)
        for target in [86, 91, 99]:
            changed = values[:target]+[99999.0]*(100-target)
            alternate = evaluate_series(changed, model)
            assert baseline.predicted[:target-86+1] == alternate.predicted[:target-86+1]
        assert evaluate_series(values, model) == baseline


def test_stable_scenario_checksum_ignores_random_ids_but_detects_changed_inputs():
    params = {'facility_id':str(uuid4()),'medicine_id':str(uuid4()),'demand_adjustment_pct':10}
    context = {'version':'scenario-1.0','medicine_code':'KEML-PARA','destination':{
        'facility_id':str(uuid4()),'facility_code':'13080','forecast_run_id':str(uuid4()),'stock':'5'}}
    expected = reproducibility_fingerprint(params, context)
    params['facility_id'] = str(uuid4())
    context['destination']['forecast_run_id'] = str(uuid4())
    assert reproducibility_fingerprint(params, context) == expected
    context['destination']['stock'] = '6'
    assert reproducibility_fingerprint(params, context) != expected


def test_frontend_path_literals_match_openapi_contract():
    import re
    from pathlib import Path
    schema = app.openapi()
    def normalize(path):
        return re.sub(r"\{[^}]+\}", "{}", path.split("?")[0])
    paths = {normalize(p.removeprefix("/api/v1")) for p in schema["paths"]}
    client = Path("frontend/src/api/client.ts").read_text()
    literals = re.findall(r"(?:['\"`])(/[^'\"`\n]+)(?:['\"`])", client)
    for literal in literals:
        literal = re.sub(r"(?<!/)\$\{[^}]+\}", "", literal)
        literal = re.sub(r"\$\{[^}]+\}", "{}", literal)
        assert normalize(literal) in paths, literal
    operations = [operation["operationId"] for methods in schema["paths"].values()
                  for method, operation in methods.items() if method in {"get", "post"}]
    assert len(operations) == len(set(operations))
