"""Kitchen orders: lifecycle, recipe-version snapshots, status history."""

from django.conf import settings
from django.db import models

from apps.core.models import BaseModel, ReasonCode
from apps.menu.models import MenuItem, RecipeVersion
from apps.pos_ingest.models import SaleEvent


class Order(BaseModel):
    """Internal order created from one POS sale event."""

    class Status(models.TextChoices):
        INGESTED = "INGESTED", "Ingested"
        IN_PREPARATION = "IN_PREPARATION", "In preparation"
        READY = "READY", "Ready"
        SERVED = "SERVED", "Served"
        RETURNED = "RETURNED", "Returned"

    sale_event = models.OneToOneField(SaleEvent, on_delete=models.PROTECT, related_name="order")
    table_ref = models.CharField(max_length=50, blank=True, default="")
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.INGESTED, db_index=True
    )
    flagged_insufficient_stock = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Order"
        verbose_name_plural = "Orders"
        indexes = [models.Index(fields=["status", "created_at"], name="order_status_created_idx")]
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"Order({self.sale_event_id}, {self.status})"


class OrderItem(BaseModel):
    """One sale line; the recipe version is snapshotted at ingestion."""

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    menu_item = models.ForeignKey(MenuItem, on_delete=models.PROTECT, null=True, blank=True)
    recipe_version = models.ForeignKey(
        RecipeVersion, on_delete=models.PROTECT, null=True, blank=True
    )
    pos_code = models.CharField(max_length=50)
    qty = models.DecimalField(max_digits=12, decimal_places=3)
    modifiers = models.JSONField(default=list, blank=True)
    price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    class Meta:
        verbose_name = "Order Item"
        verbose_name_plural = "Order Items"

    def __str__(self) -> str:
        return f"{self.pos_code} x {self.qty}"


class OrderStatusEvent(BaseModel):
    """Timestamped status transition; feeds the Service Time report."""

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="status_events")
    status = models.CharField(max_length=20, choices=Order.Status.choices)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True
    )
    reason_code = models.ForeignKey(ReasonCode, on_delete=models.PROTECT, null=True, blank=True)

    class Meta:
        verbose_name = "Order Status Event"
        verbose_name_plural = "Order Status Events"
        indexes = [models.Index(fields=["order", "created_at"], name="status_event_order_idx")]
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"{self.order_id} → {self.status}"


class OutOfStockFlag(BaseModel):
    """Chef-raised flag that a menu item cannot currently be made."""

    menu_item = models.ForeignKey(MenuItem, on_delete=models.PROTECT, related_name="oos_flags")
    flagged_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    cleared_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Out-of-Stock Flag"
        verbose_name_plural = "Out-of-Stock Flags"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"OOS({self.menu_item_id})"
