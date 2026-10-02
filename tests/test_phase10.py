from datetime import date, datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.core import (
    AnalyticalExperiment,
    Facility,
    FacilityMedicinePolicy,
    ForecastModelCode,
    ForecastPoint,
    ForecastRun,
    ForecastRunStatus,
    InventoryBalance,
    InventoryTransaction,
    Medicine,
    MLModelVersion,
    RedistributionRecommendation,
    RedistributionTransfer,
)
from app.services.analytics import aggregate_rows, evaluate_network
from app.services.experiments import ScenarioParameters, create_scenario, simulate
from app.services.forecasting import evaluate_series
from scripts.seed import DAYS, synthetic_history


def context(stock=100, safety=20, demand=5, donor_stock=150, incoming=None):
    today = date(2026, 10, 2)

    def position(name, stock):
        return {
            "facility_id": name,
            "facility_name": name,
            "transfer_eligible": True,
            "stock": str(stock),
            "safety": str(safety),
            "forecast_run_id": "run",
            "points": [[str(today + timedelta(days=i + 1)), str(demand)] for i in range(14)],
            "incoming": incoming or [],
        }

    return {
        "version": "scenario-1.0",
        "assessment_date": str(today),
        "destination": position("destination", stock),
        "donors": [position("donor", donor_stock)],
    }


def params(**kwargs):
    return ScenarioParameters(facility_id=uuid4(), medicine_id=uuid4(), **kwargs).model_dump(
        mode="json"
    )


def test_two_year_seed_is_deterministic_and_contains_disruptions():
    events = list(synthetic_history("13080", "PARA", 8, date(2026, 10, 2)))
    assert events == list(synthetic_history("13080", "PARA", 8, date(2026, 10, 2)))
    assert events != list(synthetic_history("13023", "PARA", 8, date(2026, 10, 2)))
    consumption = [e for e in events if e[0].value == "CONSUMPTION"]
    assert len(consumption) == DAYS == 730
    assert consumption[0][2] == date(2024, 10, 3)
    assert consumption[-1][2] == date(2026, 10, 2)
    assert all(consumption[i][1] == 0 for i in [*range(150, 155), *range(515, 522)])
    assert all(e[1] >= 0 for e in events)
    assert len(set(e[1] for e in consumption)) > 5


@pytest.mark.parametrize("model", list(ForecastModelCode))
def test_long_history_holdout_is_temporal(model):
    values = [float(5 + i % 7) for i in range(730)]
    first = evaluate_series(values, model, date(2024, 10, 3))
    last = evaluate_series(values[:-1] + [900.0], model, date(2024, 10, 3))
    assert first.training_observations == 716
    assert first.observations == 14
    assert first.predicted == last.predicted
    assert evaluate_series(values[:30], model) is None


@pytest.mark.parametrize(
    "field,value",
    [
        ("demand_adjustment_pct", 101),
        ("inventory_adjustment_pct", -100),
        ("lead_time_adjustment_days", -1),
        ("lead_time_adjustment_days", 31),
        ("horizon_days", 0),
    ],
)
def test_scenario_rejects_invalid_parameters(field, value):
    with pytest.raises(ValidationError):
        params(**{field: value})


def test_demand_and_inventory_adjustments_propagate_risk_and_feasibility():
    unchanged = simulate(context(), params())
    assert unchanged["baseline"] == unchanged["scenario"]
    changed = simulate(context(), params(demand_adjustment_pct=30, inventory_adjustment_pct=-30))
    assert changed["baseline"]["risk_level"] == "LOW"
    assert changed["scenario"]["risk_level"] == "HIGH"
    assert changed["scenario"]["days_to_breach"] == 8
    assert changed["scenario"]["daily_demand"] == 6.5
    assert changed["scenario"]["current_stock"] == 70
    assert changed["scenario"]["projected_shortage"] == 41
    assert changed["scenario"]["recommended_quantity"] == 41
    assert changed["scenario"]["feasible_donor"] == "donor"


def test_lead_time_delay_excludes_receipts_after_horizon():
    ctx = context(stock=30, incoming=[["2026-10-12", "60"]])
    # Supply delay affects the destination only, never donor balances.
    ctx["donors"][0]["incoming"] = []
    result = simulate(ctx, params(lead_time_adjustment_days=7))
    assert result["baseline"]["incoming_quantity"] == 60
    assert result["scenario"]["incoming_quantity"] == 0
    assert result["scenario"]["projected_shortage"] > result["baseline"]["projected_shortage"]
    assert result["scenario"]["recommended_quantity"] > result["baseline"]["recommended_quantity"]
    assert simulate(ctx, params(lead_time_adjustment_days=3))["scenario"]["incoming_quantity"] == 60


def test_donor_safety_and_network_constraints_are_respected():
    result = simulate(context(stock=0, donor_stock=30), params(demand_adjustment_pct=20))
    assert result["scenario"]["feasible_donor"] is None
    assert result["scenario"]["recommended_quantity"] == 0
    ctx = context(stock=0)
    ctx["destination"]["transfer_eligible"] = False
    assert simulate(ctx, params())["baseline"]["redistribution_feasible"] is False


def test_aggregates_pool_errors_instead_of_averaging_percentages():
    rows = [
        dict(
            model="M",
            status="MEASURED",
            observations=2,
            absolute_error=10,
            squared_error=50,
            actual_total=100,
        ),
        dict(
            model="M",
            status="MEASURED",
            observations=1,
            absolute_error=10,
            squared_error=100,
            actual_total=10,
        ),
        dict(model="M", status="INSUFFICIENT_DATA"),
    ]
    result = aggregate_rows(rows)[0]
    assert result["evaluated_series"] == 2
    assert result["observations"] == 3
    assert result["mae"] == pytest.approx(20 / 3)
    assert result["rmse"] == pytest.approx(50**0.5)
    assert result["wape"] == pytest.approx(100 * 20 / 110)


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def prepare(db):
    destination = Facility(code="D", name="Destination", transfer_eligible=True)
    donor = Facility(code="S", name="Donor", transfer_eligible=True)
    medicine = Medicine(code="M", generic_name="Paracetamol")
    model = MLModelVersion(
        code=ForecastModelCode.MOVING_AVERAGE_7D,
        name="MA",
        algorithm="MA",
        version="1",
        is_active=True,
    )
    db.add_all([destination, donor, medicine, model])
    db.flush()
    for f, stock in [(destination, 100), (donor, 150)]:
        db.add_all(
            [
                FacilityMedicinePolicy(
                    facility_id=f.id,
                    medicine_id=medicine.id,
                    safety_stock=20,
                    reorder_point=40,
                    lead_time_days=14,
                ),
                InventoryBalance(facility_id=f.id, medicine_id=medicine.id, quantity_on_hand=stock),
            ]
        )
        run = ForecastRun(
            facility_id=f.id,
            medicine_id=medicine.id,
            model_version_id=model.id,
            horizon_days=14,
            forecast_start_date=date.today() + timedelta(days=1),
            training_start_date=date.today() - timedelta(days=729),
            training_end_date=date.today(),
            data_points_used=730,
            status=ForecastRunStatus.COMPLETED,
        )
        db.add(run)
        db.flush()
        db.add_all(
            [
                ForecastPoint(
                    forecast_run_id=run.id,
                    target_date=date.today() + timedelta(days=i + 1),
                    predicted_demand=5,
                )
                for i in range(14)
            ]
        )
    db.commit()
    return destination, medicine


def authoritative_snapshot(db):
    models = [
        InventoryBalance,
        InventoryTransaction,
        ForecastRun,
        ForecastPoint,
        RedistributionRecommendation,
        RedistributionTransfer,
    ]
    return {
        m.__tablename__: sorted(str(tuple(row)) for row in db.execute(select(m.__table__)).all())
        for m in models
    }


def test_persisted_simulation_and_replay_cannot_change_authoritative_tables(db):
    facility, medicine = prepare(db)
    # Nonempty transfer history must also remain untouched.
    db.add(
        RedistributionTransfer(
            recommendation_id=uuid4(),
            source_facility_id=facility.id,
            destination_facility_id=uuid4(),
            medicine_id=medicine.id,
            quantity=5,
            status="IN_TRANSIT",
            approved_by=uuid4(),
            approved_at=datetime.now(timezone.utc),
        )
    )
    db.commit()
    before = authoritative_snapshot(db)
    result = create_scenario(
        db,
        ScenarioParameters(
            facility_id=facility.id,
            medicine_id=medicine.id,
            demand_adjustment_pct=30,
            inventory_adjustment_pct=-30,
        ),
    )
    record = db.get(AnalyticalExperiment, result["id"])
    assert result["label"] == "SIMULATION — NOT LIVE INVENTORY"
    assert simulate(record.context, record.parameters) == record.result
    assert authoritative_snapshot(db) == before
    balance = db.scalar(select(InventoryBalance).where(InventoryBalance.facility_id == facility.id))
    balance.quantity_on_hand = 1
    db.commit()
    assert (
        simulate(record.context, record.parameters) == record.result
    )  # saved inputs, not new ledger


def test_stale_forecast_is_not_silently_used(db):
    facility, medicine = prepare(db)
    for p in db.scalars(select(ForecastPoint)).all():
        p.target_date -= timedelta(days=30)
    db.commit()
    with pytest.raises(HTTPException, match="stale"):
        create_scenario(db, ScenarioParameters(facility_id=facility.id, medicine_id=medicine.id))
    assert db.scalars(select(AnalyticalExperiment)).all() == []


def test_network_evaluation_snapshot_and_insufficient_metrics(db):
    from app.models.core import InventoryTransactionType

    facility, medicine = prepare(db)
    for i in range(730):
        db.add(
            InventoryTransaction(
                facility_id=facility.id,
                medicine_id=medicine.id,
                transaction_type=InventoryTransactionType.CONSUMPTION,
                quantity=5 + i % 7,
                transaction_date=date.today() - timedelta(days=729 - i),
                created_by=uuid4(),
            )
        )
    db.commit()
    before = authoritative_snapshot(db)
    result = evaluate_network(db)
    assert result["series_count"] == 1
    assert len(result["overall"]) == 2
    assert all(row["observations"] == 14 for row in result["overall"])
    assert result["results"][0]["training_observations"] == 716
    assert len(result["context"]["inputs"][0]["values"]) == 730
    assert authoritative_snapshot(db) == before


def test_sqlite_uuid_storage_preserves_numeric_looking_identifiers(db):
    from app.models.core import InventoryTransactionType

    identifier = UUID("12345678-1234-4234-8234-123456781234")
    transaction = InventoryTransaction(
        id=identifier,
        facility_id=uuid4(),
        medicine_id=uuid4(),
        transaction_type=InventoryTransactionType.CONSUMPTION,
        quantity=2,
        transaction_date=date.today(),
        created_by=uuid4(),
    )
    db.add(transaction)
    db.commit()
    db.expire_all()
    assert db.get(InventoryTransaction, identifier).id == identifier


def test_replay_rejects_unknown_calculation_versions():
    ctx = context()
    ctx["version"] = "future-unsupported"
    with pytest.raises(HTTPException, match="version"):
        simulate(ctx, params())


def test_alembic_sqlite_upgrade_preserves_uuid_storage(tmp_path):
    import os
    import subprocess
    import sys
    from pathlib import Path

    from sqlalchemy import inspect

    filename = tmp_path / "migration.sqlite"
    url = f"sqlite:///{filename}"
    env = {**os.environ, "DATABASE_URL": url, "DEBUG": "false"}
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=Path(__file__).resolve().parents[1],
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    engine = create_engine(url)
    assert str(inspect(engine).get_columns("inventory_transactions")[0]["type"]) == "CHAR(32)"
    identifier = UUID("12345678-1234-4234-8234-123456781234")
    with Session(engine) as session:
        facility = Facility(id=identifier, code="numeric-uuid", name="Synthetic test facility")
        session.add(facility)
        session.commit()
        session.expire_all()
        assert session.get(Facility, identifier).id == identifier
    engine.dispose()
