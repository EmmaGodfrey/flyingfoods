"""Procurement models: budgets, purchase orders, GRNs, invoices, and 3-way matching."""

from django.conf import settings
from django.db import models

from apps.core.models import BaseModel, ReasonCode
from apps.masterdata.models import Product, Supplier


class PurchaseBudget(BaseModel):
    """A procurement budget request created by any authorised user.

    Travels through DRAFT → SUBMITTED → APPROVED/REJECTED. On approval the
    budget can have PurchaseOrders raised against it.
    """

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        SUBMITTED = "SUBMITTED", "Submitted"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"
        REVISION_REQUESTED = "REVISION_REQUESTED", "Revision Requested"

    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="purchase_budgets",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
    )
    total_estimated = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        verbose_name = "Purchase Budget"
        verbose_name_plural = "Purchase Budgets"
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(total_estimated__gte=0),
                name="budget_total_nonnegative",
            ),
        ]

    def __str__(self) -> str:
        return f"Budget({self.id}, {self.status})"

    def on_approval_decided(self, approval) -> None:
        """React to an Approval decision: flip status and notify receiving staff."""
        from apps.core.models import Approval
        from apps.notifications.models import Notification
        from apps.notifications.services import notify_role

        if approval.status == Approval.Status.APPROVED:
            self.status = self.Status.APPROVED
            self.save(update_fields=["status", "updated_at"])
            notify_role(
                role="RECEIVING_OFFICER",
                kind=Notification.Kind.BUDGET_APPROVED,
                body=f"Budget {self.id} has been approved and is ready for PO creation.",
                subject=self,
            )
        elif approval.status == Approval.Status.REJECTED:
            self.status = self.Status.REJECTED
            self.save(update_fields=["status", "updated_at"])


class BudgetLine(BaseModel):
    """One line item within a PurchaseBudget: product, quantity and estimated cost."""

    budget = models.ForeignKey(
        PurchaseBudget,
        on_delete=models.CASCADE,
        related_name="lines",
    )
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    qty = models.DecimalField(max_digits=12, decimal_places=3)
    est_unit_cost = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        verbose_name = "Budget Line"
        verbose_name_plural = "Budget Lines"
        constraints = [
            models.UniqueConstraint(
                fields=["budget", "product"],
                name="unique_product_per_budget",
            ),
            models.CheckConstraint(
                condition=models.Q(qty__gt=0),
                name="budget_line_qty_positive",
            ),
            models.CheckConstraint(
                condition=models.Q(est_unit_cost__gte=0),
                name="budget_cost_nonnegative",
            ),
        ]

    def __str__(self) -> str:
        return f"BudgetLine({self.budget_id}, {self.product_id}, qty={self.qty})"


class PurchaseOrder(BaseModel):
    """A purchase order raised against an approved budget for a single supplier."""

    class Status(models.TextChoices):
        CREATED = "CREATED", "Created"
        SENT = "SENT", "Sent"
        MANUAL_CONTACT_REQUIRED = "MANUAL_CONTACT_REQUIRED", "Manual Contact Required"
        PARTIALLY_RECEIVED = "PARTIALLY_RECEIVED", "Partially Received"
        RECEIVED = "RECEIVED", "Received"
        CLOSED = "CLOSED", "Closed"

    budget = models.ForeignKey(
        PurchaseBudget,
        on_delete=models.PROTECT,
        related_name="purchase_orders",
    )
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name="purchase_orders")
    po_number = models.CharField(max_length=20, unique=True)
    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.CREATED,
        db_index=True,
    )
    pdf_file = models.FileField(upload_to="procurement/po_pdfs/", null=True, blank=True)

    class Meta:
        verbose_name = "Purchase Order"
        verbose_name_plural = "Purchase Orders"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"PO({self.po_number}, {self.status})"


class POLine(BaseModel):
    """One product line within a PurchaseOrder."""

    po = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name="lines")
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    qty = models.DecimalField(max_digits=12, decimal_places=3)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    fulfilled_qty = models.DecimalField(max_digits=12, decimal_places=3, default=0)

    class Meta:
        verbose_name = "PO Line"
        verbose_name_plural = "PO Lines"
        constraints = [
            models.UniqueConstraint(
                fields=["po", "product"],
                name="unique_product_per_po",
            ),
            models.CheckConstraint(
                condition=models.Q(qty__gt=0),
                name="po_line_qty_positive",
            ),
            models.CheckConstraint(
                condition=models.Q(unit_price__gte=0),
                name="po_price_nonnegative",
            ),
            models.CheckConstraint(
                condition=models.Q(fulfilled_qty__gte=0),
                name="po_fulfilled_nonnegative",
            ),
        ]

    def __str__(self) -> str:
        return f"POLine({self.po_id}, {self.product_id}, qty={self.qty})"


class POSendLog(BaseModel):
    """Record of each attempt to send a PurchaseOrder to a supplier."""

    class Result(models.TextChoices):
        SENT = "SENT", "Sent"
        DELIVERED = "DELIVERED", "Delivered"
        BOUNCED = "BOUNCED", "Bounced"
        NONE_NO_EMAIL = "NONE_NO_EMAIL", "None — No Email"

    po = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name="send_logs")
    recipient = models.CharField(max_length=255)
    sent_at = models.DateTimeField(auto_now_add=True)
    result = models.CharField(
        max_length=20,
        choices=Result.choices,
        default=Result.NONE_NO_EMAIL,
    )

    class Meta:
        verbose_name = "PO Send Log"
        verbose_name_plural = "PO Send Logs"
        ordering = ["-sent_at"]

    def __str__(self) -> str:
        return f"POSendLog({self.po_id}, {self.result})"


class GRN(BaseModel):
    """Goods Received Note: records physical receipt of goods against a PO."""

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        POSTED = "POSTED", "Posted"

    po = models.ForeignKey(PurchaseOrder, on_delete=models.PROTECT, related_name="grns")
    received_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="grns_received",
    )
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
    )

    class Meta:
        verbose_name = "GRN"
        verbose_name_plural = "GRNs"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"GRN({self.id}, po={self.po_id}, {self.status})"


class GRNLine(BaseModel):
    """One product received within a GRN, linked to a specific PO line."""

    grn = models.ForeignKey(GRN, on_delete=models.CASCADE, related_name="lines")
    po_line = models.ForeignKey(POLine, on_delete=models.PROTECT)
    qty_received = models.DecimalField(max_digits=12, decimal_places=3)
    unit_cost = models.DecimalField(max_digits=12, decimal_places=2)
    condition = models.CharField(max_length=255, blank=True, default="")
    variance_reason = models.ForeignKey(
        ReasonCode,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = "GRN Line"
        verbose_name_plural = "GRN Lines"
        constraints = [
            models.UniqueConstraint(
                fields=["grn", "po_line"],
                name="unique_po_line_per_grn",
            ),
            models.CheckConstraint(
                condition=models.Q(qty_received__gt=0),
                name="grn_qty_positive",
            ),
            models.CheckConstraint(
                condition=models.Q(unit_cost__gte=0),
                name="grn_cost_nonnegative",
            ),
        ]

    def __str__(self) -> str:
        return f"GRNLine({self.grn_id}, {self.po_line_id}, qty={self.qty_received})"


class SupplierInvoice(BaseModel):
    """An invoice received from a supplier against a purchase order."""

    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name="invoices")
    po = models.ForeignKey(PurchaseOrder, on_delete=models.PROTECT, related_name="invoices")
    invoice_ref = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    file = models.FileField(upload_to="procurement/invoices/", null=True, blank=True)

    class Meta:
        verbose_name = "Supplier Invoice"
        verbose_name_plural = "Supplier Invoices"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["supplier", "invoice_ref"],
                name="unique_supplier_invoice_ref",
            ),
            models.CheckConstraint(
                condition=models.Q(amount__gte=0),
                name="invoice_amount_nonnegative",
            ),
        ]

    def __str__(self) -> str:
        return f"Invoice({self.invoice_ref}, {self.supplier_id})"


class InvoiceMatch(BaseModel):
    """3-way match result between a PO, GRN receipts, and the supplier invoice."""

    class Status(models.TextChoices):
        MATCHED = "MATCHED", "Matched"
        DISCREPANCY = "DISCREPANCY", "Discrepancy"
        DISPUTED = "DISPUTED", "Disputed"
        ESCALATED = "ESCALATED", "Escalated"
        RESOLVED = "RESOLVED", "Resolved"

    po = models.ForeignKey(PurchaseOrder, on_delete=models.PROTECT)
    invoice = models.OneToOneField(SupplierInvoice, on_delete=models.PROTECT)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.MATCHED,
        db_index=True,
    )
    discrepancies = models.JSONField(default=dict)

    class Meta:
        verbose_name = "Invoice Match"
        verbose_name_plural = "Invoice Matches"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"InvoiceMatch({self.id}, {self.status})"
