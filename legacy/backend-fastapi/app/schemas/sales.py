"""Schemas for POS sale creation, receipt rendering, and daily summaries."""

from datetime import date, datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class PaymentMethod(str, Enum):
    cash = "cash"
    card = "card"
    mobile = "mobile"
    split = "split"


class PaymentProvider(str, Enum):
    simulated = "simulated"


class PaymentStatus(str, Enum):
    authorized = "authorized"
    reconciled = "reconciled"


class ReconciliationJobStatus(str, Enum):
    queued = "queued"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"


class SaleLineItemCreate(BaseModel):
    product_id: int = Field(ge=1)
    quantity: Decimal = Field(gt=Decimal("0"))


class SaleTenderCreate(BaseModel):
    payment_method: PaymentMethod
    amount: Decimal = Field(ge=Decimal("0"))


class SaleCreate(BaseModel):
    payment_method: PaymentMethod
    tax_amount: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))
    discount_amount: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))
    split_tenders: list[SaleTenderCreate] | None = None
    items: list[SaleLineItemCreate] = Field(min_length=1)


class SaleLineItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    product_id: int
    quantity: Decimal
    unit_price: Decimal
    line_total: Decimal


class SaleReceipt(BaseModel):
    sale_id: int
    branch_id: int
    cashier_user_id: int | None
    payment_method: str
    subtotal: Decimal
    tax_amount: Decimal
    discount_amount: Decimal
    total: Decimal
    payment_tenders: list[SaleTenderCreate]
    created_at: datetime
    line_items: list[SaleLineItemRead]


class SalePaymentIntentRequest(BaseModel):
    provider: PaymentProvider = PaymentProvider.simulated


class SalePaymentTenderAuthorization(BaseModel):
    tender_index: int = Field(ge=0)
    payment_method: PaymentMethod
    amount: Decimal = Field(ge=Decimal("0"))
    provider: PaymentProvider
    provider_reference: str = Field(min_length=1, max_length=128)
    status: PaymentStatus


class SalePaymentIntentResult(BaseModel):
    sale_id: int
    branch_id: int
    provider: PaymentProvider
    authorized_tenders: list[SalePaymentTenderAuthorization]


class SalePaymentReconcileRequest(BaseModel):
    provider: PaymentProvider = PaymentProvider.simulated
    provider_reference: str = Field(min_length=1, max_length=128)


class SalePaymentReconcileResult(BaseModel):
    sale_id: int
    branch_id: int
    provider: PaymentProvider
    provider_reference: str
    status: PaymentStatus
    reconciled_amount: Decimal = Field(ge=Decimal("0"))
    reconciled_at: datetime


class SalePaymentReconcileJobEnqueueResult(BaseModel):
    job_id: str = Field(min_length=1, max_length=64)
    sale_id: int
    branch_id: int
    provider: PaymentProvider
    provider_reference: str
    status: ReconciliationJobStatus
    queued_at: datetime


class SalePaymentReconcileJobStatusResult(BaseModel):
    job_id: str = Field(min_length=1, max_length=64)
    sale_id: int
    branch_id: int
    provider: PaymentProvider
    provider_reference: str
    status: ReconciliationJobStatus
    queued_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    result: SalePaymentReconcileResult | None = None
    error: str | None = None


class SaleVoidRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=255)


class SaleVoidResult(BaseModel):
    sale_id: int
    status: str
    voided_at: datetime
    voided_by_user_id: int | None
    reason: str | None


class SaleRefundRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=255)


class SaleRefundResult(BaseModel):
    sale_id: int
    status: str
    refunded_at: datetime
    refunded_by_user_id: int | None
    reason: str | None


class DailySalesSummary(BaseModel):
    business_date: date
    branch_id: int
    sales_count: int
    gross_total: Decimal
    payment_method_totals: dict[str, Decimal]
