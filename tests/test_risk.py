from datetime import date, timedelta
from decimal import Decimal

from app.models.core import RiskLevel
from app.services.risk import calculate_risk, classify_risk


def points(start: date, values: list[str]):
    return [(start + timedelta(days=i), Decimal(value)) for i, value in enumerate(values)]


def test_active_stockout_is_critical():
    result = calculate_risk(
        assessment_date=date(2026, 9, 22),
        inventory_on_hand=Decimal("0"),
        safety_stock=Decimal("100"),
        forecast_points=points(date(2026, 9, 23), ["10"] * 7),
    )
    assert result.risk_level == RiskLevel.CRITICAL
    assert result.currently_out_of_stock is True
    assert result.days_to_breach == 0
    assert result.projected_stockout_date == date(2026, 9, 22)


def test_breach_in_eight_days_is_high():
    result = calculate_risk(
        assessment_date=date(2026, 9, 22),
        inventory_on_hand=Decimal("180"),
        safety_stock=Decimal("100"),
        forecast_points=points(date(2026, 9, 23), ["10"] * 10),
    )
    assert result.risk_level == RiskLevel.HIGH
    assert result.days_to_breach == 8
    assert result.projected_breach_date == date(2026, 9, 30)


def test_incoming_stock_can_delay_breach():
    result = calculate_risk(
        assessment_date=date(2026, 9, 22),
        inventory_on_hand=Decimal("150"),
        safety_stock=Decimal("100"),
        forecast_points=points(date(2026, 9, 23), ["10"] * 10),
        incoming_schedule=[(date(2026, 9, 27), Decimal("100"))],
    )
    assert result.incoming_stock_quantity == Decimal("100")
    assert result.days_to_breach is None
    assert result.risk_level == RiskLevel.LOW


def test_classification_boundaries():
    assert classify_risk(5, False) == RiskLevel.CRITICAL
    assert classify_risk(6, False) == RiskLevel.HIGH
    assert classify_risk(10, False) == RiskLevel.HIGH
    assert classify_risk(11, False) == RiskLevel.MEDIUM
    assert classify_risk(15, False) == RiskLevel.MEDIUM
    assert classify_risk(16, False) == RiskLevel.LOW
    assert classify_risk(None, False) == RiskLevel.LOW
