"""Pastel integration models: sync log and reconciliation."""

from django.conf import settings
from django.db import models

from apps.core.models import BaseModel, OutboxRecord
from apps.masterdata.models import Location, Product


class PastelSyncLog(BaseModel):
    """One attempt to push an OutboxRecord to Pastel.

    Written by the adapter after every send attempt (success or failure).
    Multiple logs per outbox record are possible when retries occur.
    """

    class Status(models.TextChoices):
        SUCCESS = "SUCCESS", "Success"
        FAILED = "FAILED", "Failed"

    outbox = models.ForeignKey(
        OutboxRecord,
        on_delete=models.PROTECT,
        related_name="sync_logs",
    )
    attempted_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=Status.choices)
    request_payload = models.JSONField()
    response = models.JSONField(null=True, blank=True)

    class Meta:
        verbose_name = "Pastel Sync Log"
        verbose_name_plural = "Pastel Sync Logs"
        ordering = ["-attempted_at"]
        indexes = [
            models.Index(fields=["status", "attempted_at"], name="pastel_log_status_at_idx"),
        ]

    def __str__(self) -> str:
        return f"PastelSyncLog({self.outbox_id}, {self.status})"


class ReconciliationRun(BaseModel):
    """A single reconciliation pass comparing our stock to Pastel's.

    Created by the nightly run_reconciliation task or triggered manually
    via the API. Lines are created for every StockBalance checked.
    """

    run_date = models.DateField()
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = "Reconciliation Run"
        verbose_name_plural = "Reconciliation Runs"
        ordering = ["-run_date", "-created_at"]

    def __str__(self) -> str:
        return f"ReconciliationRun({self.run_date})"


class ReconciliationLine(BaseModel):
    """One product/location pair compared in a ReconciliationRun.

    divergence = our_on_hand − pastel_on_hand. A non-zero divergence
    means the two systems are out of sync for this stock position.
    """

    run = models.ForeignKey(
        ReconciliationRun,
        on_delete=models.CASCADE,
        related_name="lines",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="reconciliation_lines",
    )
    location = models.ForeignKey(
        Location,
        on_delete=models.PROTECT,
        related_name="reconciliation_lines",
    )
    our_on_hand = models.DecimalField(max_digits=12, decimal_places=3)
    pastel_on_hand = models.DecimalField(max_digits=12, decimal_places=3)
    divergence = models.DecimalField(max_digits=12, decimal_places=3)

    class Meta:
        verbose_name = "Reconciliation Line"
        verbose_name_plural = "Reconciliation Lines"
        ordering = ["run", "product"]

    def __str__(self) -> str:
        return f"ReconLine({self.product_id}@{self.location_id}, div={self.divergence})"
