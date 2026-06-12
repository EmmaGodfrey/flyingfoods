"""Schema-level tests for week 3 inventory/BOM model guarantees."""

from typing import Any

from app.db.models import BillOfMaterial, Category, Product, StockMovement, Supplier, Unit


def test_week3_models_have_branch_isolation_columns() -> None:
    tenant_tables = [Category.__table__, Unit.__table__, Supplier.__table__, Product.__table__, StockMovement.__table__, BillOfMaterial.__table__]
    for table in tenant_tables:
        assert "branch_id" in table.c


def test_week3_tenant_tables_have_branch_id_indexes() -> None:
    tenant_tables = [Category.__table__, Unit.__table__, Supplier.__table__, Product.__table__, StockMovement.__table__, BillOfMaterial.__table__]
    for table in tenant_tables:
        branch_col = table.c["branch_id"]
        assert branch_col.index is True


def test_stock_movement_has_required_columns() -> None:
    table = StockMovement.__table__
    assert "product_id" in table.c
    assert "qty" in table.c
    assert "movement_type" in table.c


def test_bom_prevents_self_reference_constraint_exists() -> None:
    table: Any = BillOfMaterial.__table__
    checks = [str(getattr(c, "sqltext", "")) for c in table.constraints if c.__class__.__name__ == "CheckConstraint"]
    assert any("product_id <> ingredient_id" in sql for sql in checks)


def test_stock_movement_has_product_branch_composite_index() -> None:
    table: Any = StockMovement.__table__
    index_names = {index.name for index in table.indexes}
    assert "ix_stock_movements_product_branch" in index_names
