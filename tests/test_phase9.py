from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.api.routes.decision_support import (
    forecast_evaluation,
    forecast_explanation,
    recommendation_explanation,
    risk_explanation,
)
from app.db.base import Base
from app.models.core import (
    Facility,
    ForecastModelCode,
    ForecastPoint,
    ForecastRun,
    ForecastRunStatus,
    InventoryBalance,
    InventoryTransaction,
    InventoryTransactionType,
    Medicine,
    MLModelVersion,
    RedistributionRecommendation,
    RedistributionRecommendationStatus,
    RiskAssessment,
    RiskLevel,
)
from app.services.forecasting import _rf_features, evaluate_series


def test_temporal_holdout_metrics_and_no_future_leakage():
    values = [10.0] * 76 + [20.0] * 14
    result = evaluate_series(values, ForecastModelCode.MOVING_AVERAGE_7D)
    assert result is not None
    assert result.training_observations == 76
    assert result.observations == 14
    assert result.predicted[0] == 10.0
    assert result.predicted[1] == pytest.approx((10 * 6 + 20) / 7)
    assert result.mae == pytest.approx(sum(abs(a - p) for a, p in zip(result.actual, result.predicted)) / 14)
    assert result.rmse == pytest.approx((sum((a - p) ** 2 for a, p in zip(result.actual, result.predicted)) / 14) ** 0.5)
    assert result.wape == pytest.approx(100 * sum(abs(a - p) for a, p in zip(result.actual, result.predicted)) / sum(result.actual))
    changed = evaluate_series(values[:-1] + [1000.0], ForecastModelCode.MOVING_AVERAGE_7D)
    assert changed.predicted == result.predicted  # last target cannot affect earlier predictions


def test_models_share_holdout_and_sparse_series_have_no_metrics():
    values = [8 + i % 7 for i in range(90)]
    ma = evaluate_series(values, ForecastModelCode.MOVING_AVERAGE_7D)
    rf = evaluate_series(values, ForecastModelCode.RANDOM_FOREST)
    assert ma and rf
    assert (ma.training_observations, ma.observations) == (rf.training_observations, rf.observations) == (76, 14)
    assert evaluate_series(values[:50], ForecastModelCode.MOVING_AVERAGE_7D) is None
    assert evaluate_series([0.0] * 76 + [1.0] * 14, ForecastModelCode.RANDOM_FOREST) is None
    assert _rf_features(values, 28, date(2026, 9, 1))[-1] == (date(2026, 9, 29)).weekday()


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


def test_evaluation_api_compares_models_without_inventory_mutation(db):
    facility = Facility(code="X", name="Test Facility")
    medicine = Medicine(code="Y", generic_name="Test Medicine")
    db.add_all([facility, medicine])
    db.flush()
    start = date(2026, 1, 1)
    db.add(InventoryBalance(facility_id=facility.id, medicine_id=medicine.id, quantity_on_hand=Decimal("120")))
    for day in range(90):
        db.add(InventoryTransaction(
            facility_id=facility.id, medicine_id=medicine.id,
            transaction_type=InventoryTransactionType.CONSUMPTION,
            quantity=Decimal(10 + day % 7), transaction_date=start + timedelta(days=day),
            created_by=uuid4(),
        ))
    db.commit()
    result = forecast_evaluation(db, None, facility.id, medicine.id, start, start + timedelta(days=89), 20, 0)
    assert result["evaluated_series"] == 1
    assert {row["model"] for row in result["results"]} == {
        ForecastModelCode.MOVING_AVERAGE_7D, ForecastModelCode.RANDOM_FOREST
    }
    assert all(row["status"] == "MEASURED" and row["mae"] is not None and row["rmse"] is not None
               for row in result["results"])
    short = forecast_evaluation(db, None, facility.id, medicine.id, start, start + timedelta(days=30), 20, 0)
    assert all(row["status"] == "INSUFFICIENT_DATA" and row["mae"] is None and row["rmse"] is None
               for row in short["results"])
    assert db.scalar(select(InventoryBalance.quantity_on_hand)) == Decimal("120")


def test_explanations_are_snapshot_based_and_read_only(db):
    facility = Facility(code="F", name="Source")
    destination = Facility(code="D", name="Destination")
    medicine = Medicine(code="M", generic_name="Medicine")
    model = MLModelVersion(code=ForecastModelCode.RANDOM_FOREST, name="RF", algorithm="RandomForestRegressor", version="1")
    db.add_all([facility, destination, medicine, model])
    db.flush()
    run = ForecastRun(
        facility_id=destination.id, medicine_id=medicine.id, model_version_id=model.id,
        forecast_start_date=date(2026, 10, 1), horizon_days=2,
        training_start_date=date(2026, 7, 1), training_end_date=date(2026, 9, 30),
        data_points_used=92, status=ForecastRunStatus.COMPLETED,
    )
    db.add(run)
    db.flush()
    db.add_all([
        ForecastPoint(forecast_run_id=run.id, target_date=date(2026, 10, 1), predicted_demand=Decimal("10")),
        ForecastPoint(forecast_run_id=run.id, target_date=date(2026, 10, 2), predicted_demand=Decimal("11")),
    ])
    assessment = RiskAssessment(
        facility_id=destination.id, medicine_id=medicine.id, forecast_run_id=run.id,
        risk_level=RiskLevel.HIGH, currently_out_of_stock=False, days_to_breach=8,
        inventory_on_hand=Decimal("100"), safety_stock=Decimal("40"),
        reorder_point=Decimal("60"), incoming_stock_quantity=Decimal("5"),
        projected_shortage_units=Decimal("0"), forecast_horizon_days=2,
        calculation_version="1.0",
    )
    db.add(assessment)
    rec = RedistributionRecommendation(
        source_facility_id=facility.id, destination_facility_id=destination.id,
        medicine_id=medicine.id, status=RedistributionRecommendationStatus.PENDING_REVIEW,
        planning_horizon_days=2, source_surplus_units=Decimal("50"),
        destination_shortage_units=Decimal("20"), recommended_quantity=Decimal("20"),
        source_inventory_before=Decimal("150"), destination_inventory_before=Decimal("100"),
        source_safety_stock=Decimal("40"), destination_safety_stock=Decimal("40"),
        source_projected_end_inventory=Decimal("90"), destination_projected_end_inventory=Decimal("20"),
        constraint_results={"recommendation_feasible": True},
        expires_at=date(2026, 10, 1), created_by=uuid4(),
    )
    db.add(rec)
    db.commit()
    forecast = forecast_explanation(run.id, db, None)
    assert [feature["name"] for feature in forecast["features"]] == [
        "lag_1_consumption", "lag_7_consumption", "rolling_mean_7d",
        "rolling_mean_28d", "day_of_week",
    ]
    assert forecast["feature_importance"] is None
    risk = risk_explanation(assessment.id, db, None)
    assert risk["forecasted_demand"] == Decimal("21")
    assert risk["projected_inventory"] == Decimal("84")
    assert risk["confirmed_incoming_quantity"] == Decimal("5")
    explanation = recommendation_explanation(rec.id, db, None)
    assert explanation["source_projected_after_transfer"] == Decimal("70")
    assert explanation["recommended_quantity"] == Decimal("20")
    assert not db.dirty


def test_no_feasible_donor_and_safety_constraint_are_deterministic():
    from app.services.redistribution import calculate_stock_position
    donor = calculate_stock_position(Decimal("75"), Decimal("60"), Decimal("28"))
    shortage = calculate_stock_position(Decimal("0"), Decimal("24"), Decimal("28"))
    assert donor.current_inventory > donor.safety_stock
    assert donor.available_surplus == 0
    assert shortage.calculated_shortage > 0
    assert min(donor.available_surplus, shortage.calculated_shortage) == 0
