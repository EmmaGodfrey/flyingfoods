"""Schemas for procurement purchase orders, goods receipts, and reports."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class PurchaseOrderLineItemCreate(BaseModel):
    product_id: int = Field(ge=1)
    quantity: Decimal = Field(gt=0)
    unit_price: Decimal = Field(ge=0)


class PurchaseOrderCreate(BaseModel):
    supplier_id: int = Field(ge=1)
    notes: str | None = Field(default=None, max_length=500)
    line_items: list[PurchaseOrderLineItemCreate] = Field(min_length=1)


class SupplierCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    contact_name: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=64)
    email: str | None = Field(default=None, max_length=255)
    is_active: bool = True


class SupplierUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    contact_name: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=64)
    email: str | None = Field(default=None, max_length=255)
    is_active: bool | None = None


class SupplierRead(BaseModel):
    supplier_id: int
    branch_id: int
    name: str
    contact_name: str | None
    phone: str | None
    email: str | None
    is_active: bool
    created_at: datetime


class SupplierListResponse(BaseModel):
    items: list[SupplierRead]
    total: int
    limit: int
    offset: int


class PurchaseOrderLineItemRead(BaseModel):
    line_item_id: int
    product_id: int
    product_name: str
    quantity: Decimal
    unit_price: Decimal
    received_quantity: Decimal


class PurchaseOrderRead(BaseModel):
    purchase_order_id: int
    branch_id: int
    supplier_id: int
    supplier_name: str
    status: str
    notes: str | None
    created_by_user_id: int | None
    submitted_by_user_id: int | None
    approved_by_user_id: int | None
    submitted_at: datetime | None
    approved_at: datetime | None
    received_at: datetime | None
    closed_at: datetime | None
    created_at: datetime
    line_items: list[PurchaseOrderLineItemRead]


class PurchaseOrderListResponse(BaseModel):
    items: list[PurchaseOrderRead]
    total: int
    limit: int
    offset: int


class GoodsReceivedNoteLineCreate(BaseModel):
    purchase_order_line_item_id: int = Field(ge=1)
    quantity_received: Decimal = Field(gt=0)


class GoodsReceivedNoteCreate(BaseModel):
    purchase_order_id: int = Field(ge=1)
    reference: str | None = Field(default=None, max_length=64)
    notes: str | None = Field(default=None, max_length=500)
    line_items: list[GoodsReceivedNoteLineCreate] = Field(min_length=1)


class GoodsReceivedNoteLineRead(BaseModel):
    goods_received_note_line_item_id: int
    purchase_order_line_item_id: int
    product_id: int
    product_name: str
    quantity_received: Decimal


class GoodsReceivedNoteRead(BaseModel):
    goods_received_note_id: int
    purchase_order_id: int
    branch_id: int
    status_after_receipt: str
    reference: str | None
    notes: str | None
    received_by_user_id: int | None
    created_at: datetime
    line_items: list[GoodsReceivedNoteLineRead]


class ProcurementOrderReportLine(BaseModel):
    purchase_order_id: int
    created_at: datetime
    supplier_id: int
    supplier_name: str
    status: str
    line_count: int
    ordered_total: Decimal
    received_total: Decimal


class ProcurementOrdersReportResponse(BaseModel):
    branch_id: int
    total: int
    limit: int
    offset: int
    status: str | None
    supplier_id: int | None
    date_from: datetime | None
    date_to: datetime | None
    items: list[ProcurementOrderReportLine]
