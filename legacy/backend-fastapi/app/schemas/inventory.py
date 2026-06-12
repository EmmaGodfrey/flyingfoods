"""Schemas for inventory products, stock movements, and stock summaries."""

from decimal import Decimal
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.db.models.stock_movement import MovementType


class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    unit_id: int
    category_id: int | None = None
    supplier_id: int | None = None
    sku: str | None = Field(default=None, max_length=64)
    barcode: str | None = Field(default=None, max_length=128)
    reorder_level: Decimal = Decimal("0")
    cost_price: Decimal = Decimal("0")
    selling_price: Decimal = Decimal("0")


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    unit_id: int | None = None
    category_id: int | None = None
    supplier_id: int | None = None
    sku: str | None = Field(default=None, max_length=64)
    barcode: str | None = Field(default=None, max_length=128)
    reorder_level: Decimal | None = None
    cost_price: Decimal | None = None
    selling_price: Decimal | None = None
    is_active: bool | None = None


class ProductRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    branch_id: int
    name: str
    unit_id: int
    category_id: int | None
    supplier_id: int | None
    sku: str | None
    barcode: str | None
    reorder_level: Decimal
    cost_price: Decimal
    selling_price: Decimal
    is_active: bool


class ProductListResponse(BaseModel):
    items: list[ProductRead]
    total: int
    limit: int
    offset: int


class CategoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    branch_id: int
    name: str
    is_active: bool


class UnitRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    branch_id: int
    name: str
    symbol: str
    is_active: bool


class StockMovementCreate(BaseModel):
    product_id: int
    qty: Decimal
    movement_type: MovementType
    reference_id: str | None = Field(default=None, max_length=64)


class StockMovementRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    branch_id: int
    qty: Decimal
    movement_type: str
    reference_id: str | None
    created_by: int | None
    created_at: datetime


class StockMovementListResponse(BaseModel):
    items: list[StockMovementRead]
    total: int
    limit: int
    offset: int


class StockSummary(BaseModel):
    product_id: int
    computed_stock: Decimal


class LowStockAlert(BaseModel):
    product_id: int
    product_name: str
    reorder_level: Decimal
    computed_stock: Decimal
