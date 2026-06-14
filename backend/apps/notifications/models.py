"""Notification model: per-user in-app messages with optional deep-link subject."""

import uuid

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models

from apps.core.models import BaseModel


class Notification(BaseModel):
    """A single notification addressed to one user.

    Fan-out (one per recipient) happens at creation time in services.notify_role.
    The subject GenericFK allows deep-linking into the triggering document.
    """

    class Kind(models.TextChoices):
        BUDGET_APPROVED = "BUDGET_APPROVED", "Budget Approved"
        SYNC_FAILED = "SYNC_FAILED", "Sync Failed"
        LOW_STOCK = "LOW_STOCK", "Low Stock"
        ORDER_RETURNED = "ORDER_RETURNED", "Order Returned"
        APPROVAL_PENDING = "APPROVAL_PENDING", "Approval Pending"
        INSUFFICIENT_STOCK = "INSUFFICIENT_STOCK", "Insufficient Stock"

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    kind = models.CharField(max_length=30, choices=Kind.choices)
    subject_type = models.ForeignKey(
        ContentType,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )
    subject_id = models.UUIDField(null=True, blank=True)
    subject = GenericForeignKey("subject_type", "subject_id")
    body = models.TextField()
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["recipient", "read_at"], name="notif_recipient_read_idx"),
        ]

    def __str__(self) -> str:
        return f"Notification({self.kind}, {self.recipient_id}, read={self.read_at is not None})"
