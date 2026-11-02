"""Consumption reporting and persisted application settings through the HTTP API."""
from datetime import date
from secrets import token_urlsafe

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.security import create_access_token, hash_password
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.core import (
    AuditLog,
    Facility,
    InventoryBalance,
    InventoryTransaction,
    InventoryTransactionType,
    Medicine,
    Role,
    RoleCode,
    SystemSetting,
    User,
)
from app.services.analytics import evaluate_network
from app.services.forecasting import build_daily_consumption
from app.services.system_settings import SETTINGS_ID, get_forecast_default_horizon


@pytest.fixture
def api_fixture():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        facility = Facility(code="CONS-A", name="Consumption test facility")
        other = Facility(code="CONS-B", name="Other consumption facility")
        medicine = Medicine(
            code="CONS-M",
            generic_name="Amoxicillin",
            strength="500 mg",
            dosage_form="Capsule",
            unit_of_measure="capsules",
        )
        db.add_all([facility, other, medicine])
        db.flush()
        actors = {}
        for code in RoleCode:
            role = Role(code=code, name=code.value)
            user = User(
                email=code.value.lower() + "@consumption.example",
                full_name="Synthetic " + code.value.title(),
                role=role,
                facility_id=facility.id,
                password_hash=hash_password(token_urlsafe(18)),
                is_demo_user=True,
                is_active=True,
            )
            db.add(user)
            actors[code] = user
        db.commit()
        app.dependency_overrides[get_db] = lambda: db
        with TestClient(app, raise_server_exceptions=False) as client:
            yield client, db, actors, facility, other, medicine
        app.dependency_overrides.clear()
    engine.dispose()


def headers(user: User) -> dict[str, str]:
    return {"Authorization": "Bearer " + create_access_token(str(user.id), user.role.code.value)}


def record(client, user, facility, medicine, kind, quantity, transaction_date=None):
    return client.post(
        "/api/v1/inventory/transactions",
        headers=headers(user),
        json={
            "facility_id": str(facility.id),
            "medicine_id": str(medicine.id),
            "transaction_type": kind,
            "quantity": quantity,
            "transaction_date": str(transaction_date or date.today()),
            "reference_number": "REF-" + kind,
        },
    )


def test_consumption_log_filters_summarizes_and_enforces_facility_scope(api_fixture):
    client, db, actors, facility, other, medicine = api_fixture
    admin = actors[RoleCode.ADMINISTRATOR]
    officer = actors[RoleCode.INVENTORY_OFFICER]
    assert record(client, admin, facility, medicine, "RECEIPT", 100).status_code == 201
    assert record(client, admin, other, medicine, "RECEIPT", 100).status_code == 201
    assert record(client, officer, facility, medicine, "CONSUMPTION", 20).status_code == 201
    assert record(client, admin, other, medicine, "CONSUMPTION", 5).status_code == 201

    response = client.get("/api/v1/consumption", headers=headers(admin))
    assert response.status_code == 200
    body = response.json()
    assert body["pagination"]["total"] == 2
    assert body["summary"]["total_quantity"] == 25
    assert body["summary"]["transaction_count"] == 2
    assert body["summary"]["distinct_medicines"] == 1
    assert body["summary"]["days_covered"] == 1
    assert body["summary"]["daily_average"] == 25
    assert body["trend"] == [
        {"date": str(date.today()), "quantity": 25, "transaction_count": 2}
    ]
    assert {entry["facility_name"] for entry in body["data"]} == {
        facility.name,
        other.name,
    }
    assert all(entry["medicine_name"] == "Amoxicillin 500 mg Capsule" for entry in body["data"])
    assert all(entry["recorded_by_name"] for entry in body["data"])

    searched = client.get(
        "/api/v1/consumption",
        headers=headers(admin),
        params={"search": "Other consumption"},
    )
    assert searched.status_code == 200
    assert searched.json()["pagination"]["total"] == 1
    assert searched.json()["data"][0]["facility_id"] == str(other.id)

    sorted_rows = client.get(
        "/api/v1/consumption",
        headers=headers(admin),
        params={"sort_by": "quantity", "sort_order": "asc"},
    )
    assert [entry["quantity"] for entry in sorted_rows.json()["data"]] == [5, 20]

    filtered = client.get(
        "/api/v1/consumption",
        headers=headers(admin),
        params={"facility_id": str(other.id)},
    )
    assert filtered.status_code == 200
    assert [entry["facility_id"] for entry in filtered.json()["data"]] == [str(other.id)]

    scoped = client.get("/api/v1/consumption", headers=headers(officer))
    assert scoped.status_code == 200
    assert scoped.json()["pagination"]["total"] == 1
    assert scoped.json()["data"][0]["quantity"] == 20

    forbidden = client.get(
        "/api/v1/consumption",
        headers=headers(officer),
        params={"facility_id": str(other.id)},
    )
    assert forbidden.status_code == 403

    assert client.get(
        "/api/v1/consumption",
        headers=headers(admin),
        params={"start_date": "2026-01-02", "end_date": "2026-01-01"},
    ).status_code == 422
    assert db.scalar(select(InventoryTransaction).where(
        InventoryTransaction.transaction_type == InventoryTransactionType.CONSUMPTION
    )) is not None


def test_qa_verification_stays_in_ledger_but_is_excluded_from_analytics(api_fixture):
    client, db, actors, facility, other, medicine = api_fixture
    admin = actors[RoleCode.ADMINISTRATOR]
    assert record(client, admin, facility, medicine, "RECEIPT", 100).status_code == 201
    assert record(client, admin, facility, medicine, "CONSUMPTION", 6).status_code == 201
    assert record(client, admin, other, medicine, "RECEIPT", 10).status_code == 201

    def qa_consumption(target):
        return client.post(
            "/api/v1/inventory/transactions",
            headers=headers(admin),
            json={
                "facility_id": str(target.id),
                "medicine_id": str(medicine.id),
                "transaction_type": "CONSUMPTION",
                "quantity": 1,
                "transaction_date": str(date.today()),
                "reference_number": "QA-CONSUMPTION-VERIFY",
                "notes": "QA verification transaction; excluded from analytics",
            },
        )

    assert qa_consumption(facility).status_code == 201
    assert qa_consumption(other).status_code == 201

    daily = build_daily_consumption(db, facility.id, medicine.id, date.today(), date.today())
    assert daily == [(date.today(), 6.0)]
    assert build_daily_consumption(db, other.id, medicine.id, date.today(), date.today()) == [
        (date.today(), 0.0)
    ]

    log = client.get(
        "/api/v1/consumption",
        headers=headers(admin),
        params={"search": "QA-CONSUMPTION-VERIFY"},
    )
    assert log.status_code == 200
    assert log.json()["pagination"]["total"] == 2

    evaluation = client.get(
        "/api/v1/forecast-evaluation",
        headers=headers(admin),
        params={"facility_id": str(other.id)},
    )
    assert evaluation.status_code == 200
    assert evaluation.json()["results"] == []
    assert evaluation.json()["evaluated_series"] == 0

    network = evaluate_network(db)
    assert all(row["facility_id"] != str(other.id) for row in network["results"])


def test_recording_consumption_updates_balance_history_and_rolls_back_failures(api_fixture):
    client, db, actors, facility, _, medicine = api_fixture
    admin = actors[RoleCode.ADMINISTRATOR]
    officer = actors[RoleCode.INVENTORY_OFFICER]
    manager = actors[RoleCode.SUPPLY_CHAIN_MANAGER]

    assert record(
        client, manager, facility, medicine, "CONSUMPTION", 1
    ).status_code == 403
    assert record(client, admin, facility, medicine, "RECEIPT", 10).status_code == 201
    assert record(client, officer, facility, medicine, "CONSUMPTION", 0).status_code == 422
    insufficient = record(client, officer, facility, medicine, "CONSUMPTION", 11)
    assert insufficient.status_code == 409
    assert db.scalar(select(InventoryBalance)).quantity_on_hand == 10
    assert db.scalars(select(InventoryTransaction).where(
        InventoryTransaction.transaction_type == InventoryTransactionType.CONSUMPTION
    )).all() == []

    recorded = record(client, officer, facility, medicine, "CONSUMPTION", 4)
    assert recorded.status_code == 201
    assert recorded.json()["created_by"] == str(officer.id)
    balance = db.scalar(select(InventoryBalance))
    assert balance is not None and balance.quantity_on_hand == 6

    history = client.get("/api/v1/consumption", headers=headers(officer))
    assert history.status_code == 200
    assert history.json()["summary"] == {
        "total_quantity": 4,
        "transaction_count": 1,
        "distinct_medicines": 1,
        "days_covered": 1,
        "daily_average": 4,
        "first_date": str(date.today()),
        "last_date": str(date.today()),
    }
    assert history.json()["data"][0]["recorded_by_name"] == officer.full_name
    actions = {
        row.action for row in db.scalars(select(AuditLog)).all()
    }
    assert "INVENTORY_TRANSACTION_CREATED" in actions
    assert "SYSTEM_SETTINGS_UPDATED" not in actions


def test_settings_defaults_are_readable_update_is_admin_only_and_audited(api_fixture):
    client, db, actors, _, _, _ = api_fixture
    manager = actors[RoleCode.SUPPLY_CHAIN_MANAGER]
    admin = actors[RoleCode.ADMINISTRATOR]

    defaults = client.get("/api/v1/settings", headers=headers(manager))
    assert defaults.status_code == 200
    initial = defaults.json()
    assert initial["application_name"] == "MedStock Insight API"
    assert initial["application_version"] == "0.1.0"
    assert initial["environment"] == "test"
    assert initial["forecast_default_horizon_days"] == 30
    assert initial["reporting_default_days"] == 30
    assert initial["timezone"] == "Africa/Nairobi"
    assert initial["stockout_thresholds"] == {
        "critical_days": 5,
        "high_days": 10,
        "medium_days": 15,
        "out_of_stock_is_critical": True,
    }
    assert "database_url" not in initial
    assert "jwt" not in defaults.text.lower()

    payload = {"forecast_default_horizon_days": 7, "reporting_default_days": 90}
    assert client.post("/api/v1/settings", json=payload, headers=headers(manager)).status_code == 403
    assert client.post(
        "/api/v1/settings",
        json={"forecast_default_horizon_days": 15, "reporting_default_days": 30},
        headers=headers(admin),
    ).status_code == 422
    assert client.post(
        "/api/v1/settings",
        json={"forecast_default_horizon_days": 14, "reporting_default_days": 45},
        headers=headers(admin),
    ).status_code == 422

    updated = client.post("/api/v1/settings", json=payload, headers=headers(admin))
    assert updated.status_code == 200
    assert updated.json()["forecast_default_horizon_days"] == 7
    assert updated.json()["reporting_default_days"] == 90
    assert updated.json()["updated_by"] == str(admin.id)
    assert updated.json()["updated_by_name"] == admin.full_name

    assert client.get("/api/v1/settings", headers=headers(manager)).json()[
        "reporting_default_days"
    ] == 90
    assert db.scalar(select(SystemSetting).where(SystemSetting.id == SETTINGS_ID)) is not None
    audit = db.scalar(select(AuditLog).where(AuditLog.action == "SYSTEM_SETTINGS_UPDATED"))
    assert audit is not None and audit.new_state["forecast_default_horizon_days"] == 7
    assert get_forecast_default_horizon(db) == 7

    replaced = client.post("/api/v1/settings", json=payload, headers=headers(admin))
    assert replaced.status_code == 200
    assert len(db.scalars(select(SystemSetting)).all()) == 1
    assert len(db.scalars(select(AuditLog).where(
        AuditLog.action == "SYSTEM_SETTINGS_UPDATED"
    )).all()) == 2
