"""Core shared models: base, audit, approvals, outbox, configuration."""

import uuid

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models


class BaseModel(models.Model):
    """Abstract base model with UUID primary key and timestamps."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class ReasonCode(BaseModel):
    """Configurable categorized labels for wastage, returns, overrides."""

    class Category(models.TextChoices):
        WASTAGE = "WASTAGE", "Wastage"
        RETURN = "RETURN", "Return"
        OVERRIDE = "OVERRIDE", "Override"
        ISSUE_DAY = "ISSUE_DAY", "Off-schedule issue"
        VARIANCE = "VARIANCE", "GRN variance"

    category = models.CharField(max_length=20, choices=Category.choices, db_index=True)
    label = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Reason Code"
        verbose_name_plural = "Reason Codes"
        ordering = ["category", "label"]

    def __str__(self) -> str:
        return f"{self.category}: {self.label}"


class ThresholdConfig(BaseModel):
    """Monetary approval thresholds per workflow scope."""

    class Scope(models.TextChoices):
        TRANSFER = "TRANSFER", "Inter-unit transfer"
        WASTAGE = "WASTAGE", "Wastage / breakage"
        ADJUSTMENT = "ADJUSTMENT", "Stock-take adjustment"
        EXTRA_USAGE = "EXTRA_USAGE", "Extra ingredient usage"

    scope = models.CharField(max_length=20, choices=Scope.choices)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Threshold Configuration"
        verbose_name_plural = "Threshold Configurations"
        constraints = [
            models.UniqueConstraint(
                fields=["scope"],
                condition=models.Q(is_active=True),
                name="one_active_threshold_per_scope",
            )
        ]

    def __str__(self) -> str:
        return f"{self.scope} > {self.amount}"


class Approval(BaseModel):
    """Generic approval record shared by budgets, wastage, transfers, overrides."""

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"
        INVESTIGATION = "INVESTIGATION", "Under investigation"

    subject_type = models.ForeignKey(ContentType, on_delete=models.PROTECT)
    subject_id = models.UUIDField()
    subject = GenericForeignKey("subject_type", "subject_id")
    scope = models.CharField(max_length=20, choices=ThresholdConfig.Scope.choices, blank=True, default="")
    threshold_snapshot = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="approvals_requested"
    )
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="approvals_decided",
        null=True,
        blank=True,
    )
    reason = models.TextField(blank=True, default="")
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Approval"
        verbose_name_plural = "Approvals"
        indexes = [
            models.Index(fields=["status", "subject_type"], name="approval_status_subject_idx"),
        ]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Approval({self.scope or self.subject_type_id}, {self.status})"


class OutboxRecord(BaseModel):
    """Outbound integration record written atomically with its source document."""

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        SENDING = "SENDING", "Sending"
        SENT = "SENT", "Sent"
        FAILED = "FAILED", "Failed"
        ABANDONED = "ABANDONED", "Abandoned"

    entity_type = models.CharField(max_length=50)
    entity_id = models.UUIDField()
    payload = models.JSONField()
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    attempts = models.PositiveIntegerField(default=0)
    next_attempt_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Outbox Record"
        verbose_name_plural = "Outbox Records"
        indexes = [
            models.Index(fields=["status", "next_attempt_at"], name="outbox_status_next_idx"),
        ]
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"Outbox({self.entity_type}, {self.status})"


class IdempotencyKey(BaseModel):
    """Stored response for a client-supplied idempotency key."""

    key = models.CharField(max_length=64, unique=True)
    endpoint = models.CharField(max_length=255)
    response_snapshot = models.JSONField(null=True, blank=True)
    status_code = models.PositiveSmallIntegerField(default=200)

    class Meta:
        verbose_name = "Idempotency Key"
        verbose_name_plural = "Idempotency Keys"

    def __str__(self) -> str:
        return f"IdempotencyKey({self.key})"


class AuditLogQuerySet(models.QuerySet):
    """Append-only guard: updates and deletes are programming errors."""

    def update(self, **kwargs):  # type: ignore[override]
        raise RuntimeError("AuditLog is append-only.")

    def delete(self):  # type: ignore[override]
        raise RuntimeError("AuditLog is append-only.")


class AuditLog(BaseModel):
    """Append-only change history with before/after values."""

    entity = models.CharField(max_length=100)
    entity_id = models.UUIDField()
    action = models.CharField(max_length=40)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True
    )
    before = models.JSONField(null=True, blank=True)
    after = models.JSONField(null=True, blank=True)

    objects = AuditLogQuerySet.as_manager()

    class Meta:
        verbose_name = "Audit Log Entry"
        verbose_name_plural = "Audit Log Entries"
        indexes = [
            models.Index(fields=["entity", "entity_id"], name="audit_entity_idx"),
            models.Index(fields=["created_at"], name="audit_created_idx"),
        ]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Audit({self.entity}#{self.entity_id}, {self.action})"

    def save(self, *args, **kwargs) -> None:
        """Allow inserts only; mutating an existing row is forbidden."""
        if not self._state.adding:
            raise RuntimeError("AuditLog is append-only.")
        super().save(*args, **kwargs)


class IntegrationSettings(BaseModel):
    """Key-value integration configuration (POS, Pastel, email gateway)."""

    class Key(models.TextChoices):
        POS_MODE = "POS_MODE", "POS ingestion mode"
        POS_ENDPOINT = "POS_ENDPOINT", "POS endpoint"
        PASTEL_MODE = "PASTEL_MODE", "Pastel sync mode"
        PASTEL_CREDENTIALS = "PASTEL_CREDENTIALS", "Pastel credentials"
        EMAIL_GATEWAY = "EMAIL_GATEWAY", "Supplier email gateway"

    key = models.CharField(max_length=40, choices=Key.choices, unique=True)
    value = models.JSONField(default=dict)

    class Meta:
        verbose_name = "Integration Setting"
        verbose_name_plural = "Integration Settings"

    def __str__(self) -> str:
        return f"IntegrationSettings({self.key})"
