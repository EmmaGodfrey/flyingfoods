"""Raw POS sale events, deduplicated by the POS sale ID."""

from django.conf import settings
from django.db import models

from apps.core.models import BaseModel


class SaleEvent(BaseModel):
    """One ingested POS sale; the raw payload is kept verbatim for audit."""

    class Status(models.TextChoices):
        INGESTED = "INGESTED", "Ingested"
        FLAGGED_UNKNOWN_ITEM = "FLAGGED_UNKNOWN_ITEM", "Flagged: unknown item"
        REPLAYED = "REPLAYED", "Replayed"
        FAILED = "FAILED", "Failed"

    pos_sale_id = models.CharField(max_length=100, unique=True)
    payload = models.JSONField()
    cashier = models.CharField(max_length=100, blank=True, default="")
    sold_at = models.DateTimeField()
    totals = models.JSONField(default=dict)
    status = models.CharField(
        max_length=25, choices=Status.choices, default=Status.INGESTED, db_index=True
    )
    ingested_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Sale Event"
        verbose_name_plural = "Sale Events"
        ordering = ["-ingested_at"]

    def __str__(self) -> str:
        return f"SaleEvent({self.pos_sale_id}, {self.status})"


class ReplayLog(BaseModel):
    """Who replayed which sale event, and when."""

    sale_event = models.ForeignKey(SaleEvent, on_delete=models.PROTECT, related_name="replays")
    replayed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)

    class Meta:
        verbose_name = "Replay Log Entry"
        verbose_name_plural = "Replay Log Entries"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Replay({self.sale_event_id} by {self.replayed_by_id})"
