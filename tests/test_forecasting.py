
import pytest

from app.services.forecasting import _moving_average_predict, _random_forest_predict


def test_moving_average_forecast_is_non_negative():
    values = [10 + (i % 7) for i in range(30)]
    result = _moving_average_predict(values, horizon=14)
    assert result.mae is not None
    assert len(result.predictions) == 14
    assert all(prediction[1] >= 0 for prediction in result.predictions)
    assert all(prediction[2] is not None and prediction[3] is not None for prediction in result.predictions)


def test_random_forest_forecast_has_daily_points():
    values = [12 + (i % 7) + (i // 30) for i in range(60)]
    result = _random_forest_predict(values, horizon=21)
    assert result.mae is not None
    assert len(result.predictions) == 21
    assert all(prediction[1] >= 0 for prediction in result.predictions)


def test_random_forest_requires_minimum_history():
    with pytest.raises(ValueError, match="28 daily observations"):
        _random_forest_predict([1.0] * 20, horizon=7)
