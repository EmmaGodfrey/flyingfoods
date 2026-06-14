"""Wastage entries: extra usage, breakage, spoilage."""

from django.conf import settings
from django.db import models

from apps.core.models import BaseModel, ReasonCode
from apps.masterdata.models import Location, Product


class WastageEntry(BaseModel):
    """One wastage event; posts a stock deduction once approved or below threshold."""

    class EntryType(models.TextChoices):
        EXTRA_USAGE = "EXTRA_USAGE", "Extra usage"
        BREAKAGE = "BREAKAGE", "Breakage"
        SPOILAGE = "SPOILAGE", "Spoilage"

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        PENDING_APPROVAL = "PENDING_APPROVAL", "Pending approval"
        POSTED = "POSTED", "Posted"
        REJECTED = "REJECTED", "Rejected"

    entry_type = models.CharField(max_length=20, choices=EntryType.choices)
    order = models.ForeignKey(
        "kitchen.Order", on_delete=models.PROTECT, null=True, blank=True, related_name="wastage_entries"
    )
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    location = models.ForeignKey(Location, on_delete=models.PROTECT)
    qty = models.DecimalField(max_digits=12, decimal_places=3)
    reason_code = models.ForeignKey(ReasonCode, on_delete=models.PROTECT)
    note = models.TextField(blank=True, default="")
    value = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    logged_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)

    class Meta:
        verbose_name = "Wastage Entry"
        verbose_name_plural = "Wastage Entries"
        indexes = [
            models.Index(fields=["entry_type", "created_at"], name="wastage_type_created_idx"),
            models.Index(fields=["location", "created_at"], name="wastage_loc_created_idx"),
        ]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.entry_type} {self.product_id} x {self.qty} ({self.status})"

    def on_approval_decided(self, approval) -> None:
        """Approval-engine callback: post on approve, mark rejected otherwise."""
        from apps.core.models import Approval
        from apps.wastage.services import post_wastage_entry

        if approval.status == Approval.Status.APPROVED:
            post_wastage_entry(entry=self, posted_by=approval.decided_by, skip_approval=True)
        elif approval.status == Approval.Status.REJECTED:
            self.status = self.Status.REJECTED
            self.save(update_fields=["status", "updated_at"])
