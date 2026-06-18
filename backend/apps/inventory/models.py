"""Inventory models: the append-only stock ledger and its documents."""

from django.conf import settings
from django.db import models

from apps.core.models import BaseModel, ReasonCode
from apps.masterdata.models import Location, Product


class StockMovementQuerySet(models.QuerySet):
    """Append-only guard: ledger rows never change."""

    def update(self, **kwargs):  # type: ignore[override]
        raise RuntimeError("StockMovement is append-only.")

    def delete(self):  # type: ignore[override]
        raise RuntimeError("StockMovement is append-only.")


class StockMovement(BaseModel):
    """One immutable stock movement. Written only by `services.post_movements`."""

    class MovementType(models.TextChoices):
        SALE_DEDUCTION = "SALE_DEDUCTION", "Sale deduction"
        EXTRA_USAGE = "EXTRA_USAGE", "Extra usage"
        GRN_RECEIPT = "GRN_RECEIPT", "GRN receipt"
        ISSUE_OUT = "ISSUE_OUT", "Issue out"
        ISSUE_IN = "ISSUE_IN", "Issue in"
        TRANSFER_OUT = "TRANSFER_OUT", "Transfer out"
        TRANSFER_IN = "TRANSFER_IN", "Transfer in"
        WASTAGE = "WASTAGE", "Wastage"
        STOCKTAKE_ADJ = "STOCKTAKE_ADJ", "Stock-take adjustment"
        OVERRIDE_ADJ = "OVERRIDE_ADJ", "Override adjustment"

    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    location = models.ForeignKey(Location, on_delete=models.PROTECT)
    qty_delta = models.DecimalField(max_digits=12, decimal_places=3)
    movement_type = models.CharField(max_length=20, choices=MovementType.choices)
    document_type = models.CharField(max_length=50)
    document_id = models.UUIDField()
    unit_cost = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    posted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True
    )
    posted_at = models.DateTimeField(auto_now_add=True)

    objects = StockMovementQuerySet.as_manager()

    class Meta:
        verbose_name = "Stock Movement"
        verbose_name_plural = "Stock Movements"
        indexes = [
            models.Index(
                fields=["product", "location", "posted_at"], name="ledger_prod_loc_time_idx"
            ),
            models.Index(fields=["document_type", "document_id"], name="ledger_document_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(qty_delta=0),
                name="stock_movement_qty_nonzero",
            ),
        ]
        ordering = ["-posted_at"]

    def __str__(self) -> str:
        return f"{self.movement_type} {self.qty_delta} {self.product_id}@{self.location_id}"

    def save(self, *args, **kwargs) -> None:
        """Inserts only; the ledger has no update path."""
        if not self._state.adding:
            raise RuntimeError("StockMovement is append-only.")
        super().save(*args, **kwargs)


class StockBalance(BaseModel):
    """Cached on-hand per (product, location); derived from the ledger."""

    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    location = models.ForeignKey(Location, on_delete=models.PROTECT)
    qty_on_hand = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    last_movement_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Stock Balance"
        verbose_name_plural = "Stock Balances"
        constraints = [
            models.UniqueConstraint(
                fields=["product", "location"], name="unique_balance_per_product_location"
            )
        ]

    def __str__(self) -> str:
        return f"{self.product_id}@{self.location_id}: {self.qty_on_hand}"


class IssueNote(BaseModel):
    """Internal stock issue from Stores to Kitchen (daily) or Unit (Tue/Thu)."""

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        POSTED = "POSTED", "Posted"

    source = models.ForeignKey(Location, on_delete=models.PROTECT, related_name="issues_out")
    destination = models.ForeignKey(Location, on_delete=models.PROTECT, related_name="issues_in")
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    off_schedule_reason = models.ForeignKey(
        ReasonCode, on_delete=models.PROTECT, null=True, blank=True
    )
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)

    class Meta:
        verbose_name = "Issue Note"
        verbose_name_plural = "Issue Notes"
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(source=models.F("destination")),
                name="issue_locations_differ",
            ),
        ]

    def __str__(self) -> str:
        return f"Issue {self.source_id} → {self.destination_id} ({self.status})"


class IssueNoteLine(BaseModel):
    """One product line on an issue note."""

    issue_note = models.ForeignKey(IssueNote, on_delete=models.CASCADE, related_name="lines")
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    qty = models.DecimalField(max_digits=12, decimal_places=3)

    class Meta:
        verbose_name = "Issue Note Line"
        verbose_name_plural = "Issue Note Lines"
        constraints = [
            models.UniqueConstraint(
                fields=["issue_note", "product"],
                name="unique_product_per_issue",
            ),
            models.CheckConstraint(
                condition=models.Q(qty__gt=0),
                name="issue_line_qty_positive",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.product_id} x {self.qty}"


class Transfer(BaseModel):
    """Inter-unit stock transfer between Restaurant Kitchen and Unit."""

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        PENDING_APPROVAL = "PENDING_APPROVAL", "Pending approval"
        POSTED = "POSTED", "Posted"
        REJECTED = "REJECTED", "Rejected"

    source = models.ForeignKey(Location, on_delete=models.PROTECT, related_name="transfers_out")
    destination = models.ForeignKey(
        Location, on_delete=models.PROTECT, related_name="transfers_in"
    )
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    total_value = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        verbose_name = "Transfer"
        verbose_name_plural = "Transfers"
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(source=models.F("destination")),
                name="transfer_locations_differ",
            ),
            models.CheckConstraint(
                condition=models.Q(total_value__gte=0),
                name="transfer_value_nonnegative",
            ),
        ]

    def __str__(self) -> str:
        return f"Transfer {self.source_id} → {self.destination_id} ({self.status})"

    def on_approval_decided(self, approval) -> None:
        """Approval-engine callback: post on approve, mark rejected otherwise."""
        from apps.core.models import Approval
        from apps.inventory.services import post_transfer

        if approval.status == Approval.Status.APPROVED:
            post_transfer(transfer=self, posted_by=approval.decided_by, skip_approval=True)
        elif approval.status == Approval.Status.REJECTED:
            self.status = self.Status.REJECTED
            self.save(update_fields=["status", "updated_at"])


class TransferLine(BaseModel):
    """One product line on a transfer."""

    transfer = models.ForeignKey(Transfer, on_delete=models.CASCADE, related_name="lines")
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    qty = models.DecimalField(max_digits=12, decimal_places=3)

    class Meta:
        verbose_name = "Transfer Line"
        verbose_name_plural = "Transfer Lines"
        constraints = [
            models.UniqueConstraint(
                fields=["transfer", "product"],
                name="unique_product_per_transfer",
            ),
            models.CheckConstraint(
                condition=models.Q(qty__gt=0),
                name="transfer_line_qty_positive",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.product_id} x {self.qty}"


class StockTake(BaseModel):
    """Periodic physical count; variance posts as an adjustment."""

    class Status(models.TextChoices):
        IN_PROGRESS = "IN_PROGRESS", "In progress"
        PENDING_APPROVAL = "PENDING_APPROVAL", "Pending approval"
        POSTED = "POSTED", "Posted"

    location = models.ForeignKey(Location, on_delete=models.PROTECT)
    started_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    started_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.IN_PROGRESS
    )

    class Meta:
        verbose_name = "Stock Take"
        verbose_name_plural = "Stock Takes"
        ordering = ["-started_at"]

    def __str__(self) -> str:
        return f"StockTake {self.location_id} ({self.status})"

    def on_approval_decided(self, approval) -> None:
        """Approval-engine callback: post the adjustment when approved."""
        from apps.core.models import Approval
        from apps.inventory.services import post_stock_take

        if approval.status == Approval.Status.APPROVED:
            post_stock_take(stock_take=self, posted_by=approval.decided_by, skip_approval=True)


class StockTakeLine(BaseModel):
    """Count line: frozen system quantity vs counted quantity."""

    stock_take = models.ForeignKey(StockTake, on_delete=models.CASCADE, related_name="lines")
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    system_qty = models.DecimalField(max_digits=12, decimal_places=3)
    counted_qty = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True)
    value = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        verbose_name = "Stock Take Line"
        verbose_name_plural = "Stock Take Lines"
        constraints = [
            models.UniqueConstraint(
                fields=["stock_take", "product"], name="unique_product_per_stocktake"
            ),
            models.CheckConstraint(
                condition=models.Q(counted_qty__isnull=True) | models.Q(counted_qty__gte=0),
                name="stocktake_count_nonnegative",
            ),
            models.CheckConstraint(
                condition=models.Q(value__gte=0),
                name="stocktake_value_nonnegative",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.product_id}: sys {self.system_qty} vs counted {self.counted_qty}"

    @property
    def variance(self):
        """Counted minus system; positive means surplus."""
        if self.counted_qty is None:
            return None
        return self.counted_qty - self.system_qty
