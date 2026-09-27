from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from statistics import mean, pstdev
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.core import (
    Facility,
    ForecastModelCode,
    ForecastPoint,
    ForecastRun,
    ForecastRunStatus,
    InventoryTransaction,
    InventoryTransactionType,
    Medicine,
    MLModelVersion,
)

try:
    from sklearn.ensemble import RandomForestRegressor
except ImportError:  # pragma: no cover - runtime dependency guard
    RandomForestRegressor = None


@dataclass
class ForecastResult:
    predictions: list[tuple[date, float, float | None, float | None]]
    mae: float | None


def build_daily_consumption(
    db: Session,
    facility_id: UUID,
    medicine_id: UUID,
    start_date: date,
    end_date: date,
) -> list[tuple[date, float]]:
    rows = db.execute(
        select(InventoryTransaction.transaction_date, InventoryTransaction.quantity)
        .where(
            InventoryTransaction.facility_id == facility_id,
            InventoryTransaction.medicine_id == medicine_id,
            InventoryTransaction.transaction_type == InventoryTransactionType.CONSUMPTION,
            InventoryTransaction.transaction_date >= start_date,
            InventoryTransaction.transaction_date <= end_date,
        )
        .order_by(InventoryTransaction.transaction_date)
    ).all()

    totals: dict[date, float] = {}
    for transaction_date, quantity in rows:
        totals[transaction_date] = totals.get(transaction_date, 0.0) + float(quantity)

    result: list[tuple[date, float]] = []
    cursor = start_date
    while cursor <= end_date:
        result.append((cursor, totals.get(cursor, 0.0)))
        cursor += timedelta(days=1)
    return result


def _moving_average_predict(values: list[float], horizon: int, window: int = 7) -> ForecastResult:
    if len(values) < window:
        raise ValueError(f"At least {window} historical observations are required")

    holdout = min(7, max(1, len(values) // 5))
    train = values[:-holdout]
    actual = values[-holdout:]
    evaluation_predictions: list[float] = []
    history = train[:]
    for actual_value in actual:
        prediction = mean(history[-window:])
        evaluation_predictions.append(prediction)
        history.append(actual_value)
    mae = mean(abs(a - p) for a, p in zip(actual, evaluation_predictions))

    history = values[:]
    point_values: list[float] = []
    for _ in range(horizon):
        prediction = max(0.0, mean(history[-window:]))
        point_values.append(prediction)
        history.append(prediction)

    residuals = [a - p for a, p in zip(actual, evaluation_predictions)]
    residual_std = pstdev(residuals) if len(residuals) > 1 else 0.0
    margin = 1.96 * residual_std
    return ForecastResult(
        predictions=[(date.today(), value, max(0.0, value - margin), value + margin) for value in point_values],
        mae=mae,
    )


def _rf_features(series: list[float], index: int) -> list[float]:
    return [
        series[index - 1],
        series[index - 7],
        mean(series[index - 7 : index]),
        mean(series[max(0, index - 28) : index]),
        float(index % 7),
    ]


def _random_forest_predict(values: list[float], horizon: int) -> ForecastResult:
    if RandomForestRegressor is None:
        raise RuntimeError("scikit-learn is required for RANDOM_FOREST forecasts")
    if len(values) < 28:
        raise ValueError("At least 28 daily observations are required for RANDOM_FOREST")

    holdout = min(7, max(3, len(values) // 8))
    split = len(values) - holdout
    train_values = values[:split]

    x_train = [_rf_features(train_values, i) for i in range(28, len(train_values))]
    y_train = train_values[28:]
    if not x_train:
        raise ValueError("Insufficient observations after feature construction")

    model = RandomForestRegressor(
        n_estimators=200,
        max_depth=12,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1,
    )
    model.fit(x_train, y_train)

    eval_history = train_values[:]
    eval_predictions: list[float] = []
    for idx in range(split, len(values)):
        pred = max(0.0, float(model.predict([_rf_features(eval_history, len(eval_history))])[0]))
        eval_predictions.append(pred)
        eval_history.append(values[idx])
    mae = mean(abs(a - p) for a, p in zip(values[split:], eval_predictions))

    full_x = [_rf_features(values, i) for i in range(28, len(values))]
    full_y = values[28:]
    full_model = RandomForestRegressor(
        n_estimators=200,
        max_depth=12,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1,
    )
    full_model.fit(full_x, full_y)

    history = values[:]
    predictions: list[float] = []
    for _ in range(horizon):
        pred = max(0.0, float(full_model.predict([_rf_features(history, len(history))])[0]))
        predictions.append(pred)
        history.append(pred)

    residuals = [a - p for a, p in zip(values[split:], eval_predictions)]
    residual_std = pstdev(residuals) if len(residuals) > 1 else 0.0
    margin = 1.96 * residual_std
    return ForecastResult(
        predictions=[(date.today(), value, max(0.0, value - margin), value + margin) for value in predictions],
        mae=mae,
    )


def _forecast_result(values: list[float], model_code: ForecastModelCode, horizon: int) -> ForecastResult:
    if model_code == ForecastModelCode.MOVING_AVERAGE_7D:
        return _moving_average_predict(values, horizon)
    if model_code == ForecastModelCode.RANDOM_FOREST:
        return _random_forest_predict(values, horizon)
    raise ValueError(f"Unsupported model: {model_code}")


def generate_forecast(
    db: Session,
    facility_id: UUID,
    medicine_id: UUID,
    model_code: ForecastModelCode,
    horizon_days: int,
    lookback_days: int,
) -> ForecastRun:
    facility = db.get(Facility, facility_id)
    medicine = db.get(Medicine, medicine_id)
    if facility is None or not facility.is_active:
        raise HTTPException(status_code=404, detail="Facility not found")
    if medicine is None or not medicine.is_active:
        raise HTTPException(status_code=404, detail="Medicine not found")

    model_version = db.scalar(
        select(MLModelVersion).where(MLModelVersion.code == model_code, MLModelVersion.is_active.is_(True))
    )
    if model_version is None:
        raise HTTPException(status_code=400, detail=f"Forecast model {model_code} is not configured")

    today = date.today()
    start_date = today - timedelta(days=lookback_days - 1)
    daily = build_daily_consumption(db, facility_id, medicine_id, start_date, today)
    values = [value for _, value in daily]

    if sum(1 for value in values if value > 0) < 7:
        raise HTTPException(
            status_code=422,
            detail="Insufficient consumption history: at least 7 non-zero consumption days are required",
        )

    if model_code == ForecastModelCode.RANDOM_FOREST and len(values) < 28:
        raise HTTPException(status_code=422, detail="RANDOM_FOREST requires at least 28 daily observations")

    try:
        result = _forecast_result(values, model_code, horizon_days)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    forecast_start = today + timedelta(days=1)
    run = ForecastRun(
        facility_id=facility_id,
        medicine_id=medicine_id,
        model_version_id=model_version.id,
        forecast_start_date=forecast_start,
        horizon_days=horizon_days,
        training_start_date=start_date,
        training_end_date=today,
        data_points_used=len(values),
        mae=Decimal(str(round(result.mae, 4))) if result.mae is not None else None,
        status=ForecastRunStatus.COMPLETED,
    )
    db.add(run)
    db.flush()

    for offset, (target_date, predicted, lower, upper) in enumerate(result.predictions, start=1):
        actual_date = forecast_start + timedelta(days=offset - 1)
        db.add(
            ForecastPoint(
                forecast_run_id=run.id,
                target_date=actual_date,
                predicted_demand=Decimal(str(round(predicted, 4))),
                lower_bound=Decimal(str(round(lower, 4))) if lower is not None else None,
                upper_bound=Decimal(str(round(upper, 4))) if upper is not None else None,
            )
        )
    db.commit()
    db.refresh(run)
    return run
