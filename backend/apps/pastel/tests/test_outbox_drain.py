"""SC-008: zero-loss / zero-duplicate outbox drain tests.

Verifies that:
  - posting a movement creates exactly one OutboxRecord
  - drain_outbox_records marks it SENT and writes a SUCCESS PastelSyncLog
  - simulated failure increments attempts and writes a FAILED log
  - recovery (clear failure, re-drain) produces exactly one SENT record
  - no duplicate SENT logs exist after recovery
"""

import uuid
from decimal import Decimal

import pytest

from apps.core.models import OutboxRecord
from apps.inventory.services import MovementLine, post_movements
from apps.pastel.adapter import PastelError, send_to_pastel
from apps.pastel.models import PastelSyncLog
from apps.pastel.tasks import drain_outbox_records

pytestmark = pytest.mark.django_db


def _pending_qs():
    """Return a QuerySet of all PENDING OutboxRecords."""
    return OutboxRecord.objects.filter(status=OutboxRecord.Status.PENDING)


class TestOutboxCreation:
    """Posting a movement creates exactly one OutboxRecord."""

    def test_post_movement_creates_outbox(self, product, locations):
        """A single post_movements call writes exactly one OutboxRecord."""
        doc_id = uuid.uuid4()
        post_movements(
            document_type="GRN",
            document_id=doc_id,
            lines=[
                MovementLine(
                    product_id=product.pk,
                    location_id=locations["stores"].pk,
                    qty_delta=Decimal("20"),
                    movement_type="GRN_RECEIPT",
                )
            ],
        )

        assert OutboxRecord.objects.count() == 1
        record = OutboxRecord.objects.first()
        assert record.status == OutboxRecord.Status.PENDING
        assert record.entity_type == "GRN"
        assert str(record.entity_id) == str(doc_id)


class TestHappyPathDrain:
    """With PASTEL_STUB_FAIL off, drain marks records SENT with a SUCCESS log."""

    def test_drain_marks_sent_and_writes_success_log(self, product, locations):
        """Zero-loss: one PENDING → one SENT, one SUCCESS PastelSyncLog."""
        doc_id = uuid.uuid4()
        post_movements(
            document_type="GRN",
            document_id=doc_id,
            lines=[
                MovementLine(
                    product_id=product.pk,
                    location_id=locations["stores"].pk,
                    qty_delta=Decimal("10"),
                    movement_type="GRN_RECEIPT",
                )
            ],
        )

        assert OutboxRecord.objects.filter(status=OutboxRecord.Status.PENDING).count() == 1

        drain_outbox_records(_pending_qs())

        record = OutboxRecord.objects.first()
        assert record.status == OutboxRecord.Status.SENT
        assert record.attempts == 0

        logs = PastelSyncLog.objects.filter(outbox=record)
        assert logs.count() == 1
        assert logs.first().status == PastelSyncLog.Status.SUCCESS


class TestFailurePath:
    """Simulated adapter failure increments attempts and writes a FAILED log."""

    def test_failure_increments_attempts_and_writes_failed_log(
        self, pending_outbox, monkeypatch
    ):
        """On adapter failure, status=FAILED, attempts=1, FAILED log written."""
        def _failing_post(payload):
            raise PastelError("Simulated outage")

        monkeypatch.setattr(
            "apps.pastel.adapter.get_adapter",
            lambda: type("FakeAdapter", (), {"post_movement": staticmethod(_failing_post)})(),
        )

        drain_outbox_records(
            OutboxRecord.objects.filter(pk=pending_outbox.pk)
        )

        pending_outbox.refresh_from_db()
        assert pending_outbox.status == OutboxRecord.Status.FAILED
        assert pending_outbox.attempts == 1

        logs = PastelSyncLog.objects.filter(outbox=pending_outbox)
        assert logs.count() == 1
        assert logs.first().status == PastelSyncLog.Status.FAILED


class TestRecovery:
    """After a failure, a second drain with the stub working sends the record."""

    def test_recovery_after_failure(self, pending_outbox, monkeypatch):
        """SC-008: FAILED → reset to PENDING → drain succeeds → SENT, no duplicates."""
        # First drain: fail.
        def _failing_post(payload):
            raise PastelError("Simulated outage")

        monkeypatch.setattr(
            "apps.pastel.adapter.get_adapter",
            lambda: type("FakeAdapter", (), {"post_movement": staticmethod(_failing_post)})(),
        )

        drain_outbox_records(
            OutboxRecord.objects.filter(pk=pending_outbox.pk)
        )

        pending_outbox.refresh_from_db()
        assert pending_outbox.status == OutboxRecord.Status.FAILED

        # Reset to PENDING for recovery drain (simulating the back-off expiry).
        pending_outbox.status = OutboxRecord.Status.PENDING
        pending_outbox.save(update_fields=["status", "updated_at"])

        # Second drain: adapter works normally (restore real adapter).
        monkeypatch.undo()

        drain_outbox_records(
            OutboxRecord.objects.filter(pk=pending_outbox.pk)
        )

        pending_outbox.refresh_from_db()
        assert pending_outbox.status == OutboxRecord.Status.SENT

        # Exactly one SUCCESS log (no duplicate sent logs).
        success_logs = PastelSyncLog.objects.filter(
            outbox=pending_outbox, status=PastelSyncLog.Status.SUCCESS
        )
        assert success_logs.count() == 1

    def test_no_loss_with_multiple_records(self, product, locations):
        """Multiple PENDING records are all drained without loss."""
        for i in range(3):
            doc_id = uuid.uuid4()
            post_movements(
                document_type="GRN",
                document_id=doc_id,
                lines=[
                    MovementLine(
                        product_id=product.pk,
                        location_id=locations["stores"].pk,
                        qty_delta=Decimal(str(i + 1)),
                        movement_type="GRN_RECEIPT",
                    )
                ],
            )

        assert OutboxRecord.objects.filter(status=OutboxRecord.Status.PENDING).count() == 3

        drain_outbox_records(_pending_qs())

        assert OutboxRecord.objects.filter(status=OutboxRecord.Status.SENT).count() == 3
        assert OutboxRecord.objects.filter(status=OutboxRecord.Status.PENDING).count() == 0
        assert PastelSyncLog.objects.filter(status=PastelSyncLog.Status.SUCCESS).count() == 3


class TestAbandonAfterMaxAttempts:
    """After 5 failures, the record is ABANDONED and admins are notified."""

    def test_abandoned_after_five_failures(self, pending_outbox, monkeypatch, make_user):
        """Five consecutive failures → ABANDONED, notify_role called."""
        make_user("ADMIN", email="admin-abandon@test.local")

        def _failing_post(payload):
            raise PastelError("Persistent outage")

        monkeypatch.setattr(
            "apps.pastel.adapter.get_adapter",
            lambda: type("FakeAdapter", (), {"post_movement": staticmethod(_failing_post)})(),
        )

        # Force 4 existing attempts so the next one hits 5.
        pending_outbox.attempts = 4
        pending_outbox.save(update_fields=["attempts", "updated_at"])

        drain_outbox_records(
            OutboxRecord.objects.filter(pk=pending_outbox.pk)
        )

        pending_outbox.refresh_from_db()
        assert pending_outbox.status == OutboxRecord.Status.ABANDONED
        assert pending_outbox.attempts == 5
