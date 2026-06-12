"""Schemas for reporting endpoints and async report task polling."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, Field


class ReportTaskStatus(str, Enum):
    queued = "queued"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"


class SalesReportLine(BaseModel):
    sale_id: int
    sold_at: datetime
    cashier_user_id: int | None
    payment_method: str
    product_id: int
    product_name: str
    quantity: Decimal
    unit_price: Decimal
    line_total: Decimal


class SalesReportTotals(BaseModel):
    sale_count: int
    line_count: int
    quantity_total: Decimal
    gross_total: Decimal


class SalesReportResponse(BaseModel):
    branch_id: int
    date_from: datetime | None
    date_to: datetime | None
    payment_method: str | None
    cashier_user_id: int | None
    product_id: int | None
    totals: SalesReportTotals
    lines: list[SalesReportLine]


class InventoryValuationLine(BaseModel):
    product_id: int
    product_name: str
    supplier_id: int | None
    computed_stock: Decimal
    cost_price: Decimal
    valuation: Decimal


class InventoryValuationResponse(BaseModel):
    branch_id: int
    total_valuation: Decimal
    items: list[InventoryValuationLine]


class InventoryMovementReportLine(BaseModel):
    movement_id: int
    occurred_at: datetime
    movement_type: str
    product_id: int
    product_name: str
    qty: Decimal
    reference_id: str | None
    created_by: int | None


class InventoryMovementReportResponse(BaseModel):
    branch_id: int
    total: int
    limit: int
    offset: int
    movement_type: str | None
    product_id: int | None
    date_from: datetime | None
    date_to: datetime | None
    items: list[InventoryMovementReportLine]


class ProcurementSpendLine(BaseModel):
    month: str = Field(pattern=r"^\d{4}-\d{2}$")
    supplier_id: int | None
    supplier_name: str
    total_spend: Decimal


class ProcurementSpendResponse(BaseModel):
    branch_id: int
    date_from: datetime | None
    date_to: datetime | None
    rows: list[ProcurementSpendLine]


class ReportTaskEnqueueResponse(BaseModel):
    task_id: str = Field(min_length=1, max_length=128)
    branch_id: int
    status: ReportTaskStatus
    report_type: str


class ReportTaskStatusResponse(BaseModel):
    task_id: str = Field(min_length=1, max_length=128)
    branch_id: int
    status: ReportTaskStatus
    report_type: str
    result: ProcurementSpendResponse | None = None
    error: str | None = None
