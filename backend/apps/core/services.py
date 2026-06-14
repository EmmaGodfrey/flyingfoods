"""Core write services: audit logging and the shared approval engine."""

from decimal import Decimal
from typing import Any, Optional

from django.contrib.contenttypes.models import ContentType
from django.db import models, transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.core.models import Approval, AuditLog, ThresholdConfig


def log_audit(
    *,
    entity: str,
    entity_id: Any,
    action: str,
    user: Optional[Any] = None,
    before: Optional[dict] = None,
    after: Optional[dict] = None,
) -> AuditLog:
    """Append one audit entry. Never updates, never deletes."""
    return AuditLog.objects.create(
        entity=entity,
        entity_id=entity_id,
        action=action,
        user=user,
        before=before,
        after=after,
    )


def get_active_threshold(scope: str) -> Optional[Decimal]:
    """Return the active monetary threshold for a scope, or None when unset."""
    row = (
        ThresholdConfig.objects.filter(scope=scope, is_active=True)
        .only("amount")
        .first()
    )
    return row.amount if row else None


def requires_approval(scope: str, value: Decimal) -> bool:
    """True when a monetary value exceeds the active threshold for its scope."""
    threshold = get_active_threshold(scope)
    if threshold is None:
        return False
    return value > threshold


def submit_for_approval(
    *,
    subject: models.Model,
    scope: str,
    requested_by: Any,
    value: Optional[Decimal] = None,
) -> Approval:
    """Create a PENDING approval, snapshotting the threshold in force right now."""
    approval = Approval.objects.create(
        subject_type=ContentType.objects.get_for_model(type(subject)),
        subject_id=subject.pk,
        scope=scope,
        threshold_snapshot=get_active_threshold(scope) if value is not None else None,
        requested_by=requested_by,
    )
    log_audit(
        entity="Approval",
        entity_id=approval.pk,
        action="SUBMIT",
        user=requested_by,
        after={"scope": scope, "subject_id": str(subject.pk)},
    )
    return approval


@transaction.atomic
def decide_approval(*, approval: Approval, decided_by: Any, decision: str, reason: str = "") -> Approval:
    """Apply a Manager decision and notify the subject document via callback.

    The subject model may define `on_approval_decided(approval)` to react
    (post stock, unblock an order, reject a budget). Decisions are final
    except INVESTIGATION, which may be decided again.
    """
    valid = {Approval.Status.APPROVED, Approval.Status.REJECTED, Approval.Status.INVESTIGATION}
    if decision not in valid:
        raise ValidationError({"decision": "Invalid decision."})
    if approval.status not in (Approval.Status.PENDING, Approval.Status.INVESTIGATION):
        raise ValidationError({"decision": "Approval already finalised."})
    if decision == Approval.Status.REJECTED and not reason:
        raise ValidationError({"reason": "Reason is required when rejecting."})

    before = approval.status
    approval.status = decision
    approval.decided_by = decided_by
    approval.reason = reason
    approval.decided_at = timezone.now()
    approval.save(update_fields=["status", "decided_by", "reason", "decided_at", "updated_at"])

    log_audit(
        entity="Approval",
        entity_id=approval.pk,
        action=decision,
        user=decided_by,
        before={"status": before},
        after={"status": decision, "reason": reason},
    )

    subject = approval.subject
    if subject is not None and hasattr(subject, "on_approval_decided"):
        subject.on_approval_decided(approval)
    return approval
