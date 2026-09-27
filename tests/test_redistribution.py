from decimal import Decimal

from app.services.redistribution import calculate_stock_position


def test_surplus_preserves_safety_stock():
    position = calculate_stock_position(
        current_inventory=Decimal("1000"),
        safety_stock=Decimal("250"),
        forecast_demand=Decimal("300"),
    )
    assert position.projected_end_inventory == Decimal("700.00")
    assert position.available_surplus == Decimal("450.00")
    assert position.calculated_shortage == Decimal("0.00")


def test_shortage_is_amount_below_safety_stock():
    position = calculate_stock_position(
        current_inventory=Decimal("400"),
        safety_stock=Decimal("250"),
        forecast_demand=Decimal("300"),
    )
    assert position.projected_end_inventory == Decimal("100.00")
    assert position.available_surplus == Decimal("0.00")
    assert position.calculated_shortage == Decimal("150.00")


def test_recommendation_quantity_is_bounded_by_source_and_destination():
    donor = calculate_stock_position(Decimal("1000"), Decimal("250"), Decimal("300"))
    receiver = calculate_stock_position(Decimal("400"), Decimal("250"), Decimal("300"), incoming_stock=Decimal("100"))
    quantity = min(donor.available_surplus, receiver.calculated_shortage)
    assert quantity == Decimal("50.00")
