"""Celery tasks for Pastel integration: outbox drain, batch sync, reconciliation.

Task names must match what config/celery.py registers in beat_schedule:
  apps.pastel.tasks.drain_outbox
  apps.pastel.tasks.daily_batch_sync
  apps.pastel.tasks.run_reconciliation
"""

import datetime
import logging
import uuid
from decimal import Decimal

from celery import shared_task
from django.utils import timezone

from apps.core.models import OutboxRecord

logger = logging.getLogger(__name__)


def _process_outbox_record(record: OutboxRecord) -> None:
    """Attempt to send one OutboxRecord and update its status in-place.

    Sets the record to SENDING before the call, then SENT on success or
    FAILED on error. After 5 failures the record is ABANDONED and all
    admins receive a SYNC_FAILED notification.

    Args:
        record: An OutboxRecord in PENDING state to process.
    """
    from apps.notifications.services import notify_role
    from apps.pastel.adapter import send_to_pastel

    record.status = OutboxRecord.Status.SENDING
    record.save(update_fields=["status", "updated_at"])

    success = send_to_pastel(record)

    if success:
        record.status = OutboxRecord.Status.SENT
        record.save(update_fields=["status", "updated_at"])
        return

    record.attempts += 1
    backoff_minutes = 2 ** record.attempts
    record.next_attempt_at = timezone.now() + datetime.timedelta(minutes=backoff_minutes)
    record.status = OutboxRecord.Status.FAILED

    if record.attempts >= 5:
        record.status = OutboxRecord.Status.ABANDONED
        record.save(update_fields=["status", "attempts", "next_attempt_at", "updated_at"])
        logger.error(
            "OutboxRecord %s abandoned after %d attempts.", record.pk, record.attempts
        )
        notify_role(
            role="ADMIN",
            kind="SYNC_FAILED",
            body=(
                f"Pastel sync permanently failed for outbox record {record.pk} "
                f"({record.entity_type} / {record.entity_id}) after "
                f"{record.attempts} attempts."
            ),
        )
        return

    record.save(update_fields=["status", "attempts", "next_attempt_at", "updated_at"])
    logger.warning(
        "OutboxRecord %s failed (attempt %d); next retry in %d min.",
        record.pk,
        record.attempts,
        backoff_minutes,
    )


def drain_outbox_records(queryset) -> int:
    """Process every record in the given queryset.

    Wraps each record in its own try/except so one failure never stops the
    rest of the batch. Returns the count of records processed.

    Args:
        queryset: A QuerySet of OutboxRecord rows to process.

    Returns:
        Number of records attempted.
    """
    count = 0
    for record in queryset.iterator():
        try:
            _process_outbox_record(record)
        except Exception:
            logger.exception(
                "Unexpected error processing OutboxRecord %s — skipping.", record.pk
            )
        count += 1
    return count


@shared_task(name="apps.pastel.tasks.drain_outbox")
def drain_outbox() -> str:
    """Send all due PENDING OutboxRecords to Pastel.

    Runs every 30 seconds via Celery Beat. Picks up any record that is
    PENDING and whose next_attempt_at is in the past.

    Returns:
        A summary string for the Celery result backend.
    """
    now = timezone.now()
    pending = OutboxRecord.objects.filter(
        status=OutboxRecord.Status.PENDING,
        next_attempt_at__lte=now,
    )
    processed = drain_outbox_records(pending)
    return f"drain_outbox: processed {processed} record(s)."


@shared_task(name="apps.pastel.tasks.daily_batch_sync")
def daily_batch_sync() -> str:
    """End-of-day sweep: catch any PENDING records that slipped through.

    Runs at 23:30 via Celery Beat. Processes all PENDING records regardless
    of their next_attempt_at schedule, ensuring nothing is left behind.

    Returns:
        A summary string for the Celery result backend.
    """
    pending = OutboxRecord.objects.filter(status=OutboxRecord.Status.PENDING)
    processed = drain_outbox_records(pending)
    return f"daily_batch_sync: processed {processed} record(s)."


def run_reconciliation_now() -> uuid.UUID:
    """Execute a reconciliation and return the ReconciliationRun id.

    Compares every StockBalance row against Pastel's on-hand figure, writes
    one ReconciliationLine per balance, and returns the run's UUID. This is
    the reusable core called by both the Celery task and the API view.

    Returns:
        UUID of the newly created ReconciliationRun.
    """
    from apps.inventory.models import StockBalance
    from apps.pastel.adapter import get_adapter
    from apps.pastel.models import ReconciliationLine, ReconciliationRun

    today = datetime.date.today()
    run = ReconciliationRun.objects.create(run_date=today)

    adapter = get_adapter()
    balances = StockBalance.objects.select_related("product", "location").iterator()

    lines = []
    for balance in balances:
        product_code = balance.product.pastel_code or balance.product.code
        our_qty: Decimal = balance.qty_on_hand
        try:
            pastel_qty: Decimal = adapter.get_on_hand(  # type: ignore[attr-defined]
                product_code, balance.location.name
            )
        except Exception:
            logger.exception(
                "Could not get Pastel on-hand for %s @ %s.",
                product_code,
                balance.location.name,
            )
            pastel_qty = Decimal("0")

        divergence = our_qty - pastel_qty
        lines.append(
            ReconciliationLine(
                run=run,
                product=balance.product,
                location=balance.location,
                our_on_hand=our_qty,
                pastel_on_hand=pastel_qty,
                divergence=divergence,
            )
        )

    if lines:
        ReconciliationLine.objects.bulk_create(lines)

    logger.info(
        "ReconciliationRun %s: %d line(s) created for %s.",
        run.pk,
        len(lines),
        today,
    )
    return run.pk


@shared_task(name="apps.pastel.tasks.run_reconciliation")
def run_reconciliation() -> str:
    """Nightly reconciliation task.

    Runs at 23:45 via Celery Beat. Delegates to run_reconciliation_now().

    Returns:
        A summary string for the Celery result backend.
    """
    run_id = run_reconciliation_now()
    return f"run_reconciliation: created run {run_id}."
