"""Unit tests for week 4 inventory service helper behavior."""

from decimal import Decimal

from app.services.inventory_service import evaluate_low_stock_rows, stock_cache_key


def test_stock_cache_key_uses_branch_id() -> None:
    assert stock_cache_key(42) == "inventory:stock:branch:42"


def test_evaluate_low_stock_rows_flags_only_below_threshold() -> None:
    rows = [
        (1, "Burger Bun", Decimal("20.00"), Decimal("5.00")),
        (2, "Beef Patty", Decimal("10.00"), Decimal("10.00")),
        (3, "Burger", Decimal("15.00"), Decimal("25.00")),
    ]

    alerts = evaluate_low_stock_rows(rows)

    assert len(alerts) == 1
    assert alerts[0].product_id == 1
    assert alerts[0].product_name == "Burger Bun"
    assert alerts[0].computed_stock == Decimal("5.00")
