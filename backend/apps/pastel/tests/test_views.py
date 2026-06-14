"""View tests for the Pastel integration API endpoints."""

import uuid
from decimal import Decimal

import pytest
from django.urls import reverse

from apps.core.models import OutboxRecord
from apps.pastel.models import PastelSyncLog

pytestmark = pytest.mark.django_db


def _make_outbox(status=OutboxRecord.Status.PENDING) -> OutboxRecord:
    return OutboxRecord.objects.create(
        entity_type="GRN",
        entity_id=uuid.uuid4(),
        payload={"document_type": "GRN", "lines": []},
        status=status,
    )


def _make_sync_log(outbox: OutboxRecord, log_status=PastelSyncLog.Status.SUCCESS):
    return PastelSyncLog.objects.create(
        outbox=outbox,
        status=log_status,
        request_payload=outbox.payload,
        response={"status": "ok"},
    )


class TestSyncLogList:
    """GET /api/pastel/sync-log/ — requires IsAdmin."""

    def test_admin_can_list_sync_logs(self, auth_client):
        """Admin receives 200 with a list of sync logs."""
        outbox = _make_outbox(OutboxRecord.Status.SENT)
        _make_sync_log(outbox)

        client = auth_client("ADMIN")
        response = client.get("/api/pastel/sync-log/")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["count"] >= 1

    def test_non_admin_is_forbidden(self, auth_client):
        """Manager receives 403 on sync-log list."""
        client = auth_client("MANAGER")
        response = client.get("/api/pastel/sync-log/")
        assert response.status_code == 403

    def test_anonymous_is_unauthorized(self, api_client):
        """Unauthenticated request receives 401."""
        response = api_client.get("/api/pastel/sync-log/")
        assert response.status_code == 401

    def test_filter_by_status(self, auth_client):
        """?status=FAILED returns only FAILED logs."""
        outbox_ok = _make_outbox(OutboxRecord.Status.SENT)
        _make_sync_log(outbox_ok, PastelSyncLog.Status.SUCCESS)

        outbox_fail = _make_outbox(OutboxRecord.Status.FAILED)
        _make_sync_log(outbox_fail, PastelSyncLog.Status.FAILED)

        client = auth_client("ADMIN")
        response = client.get("/api/pastel/sync-log/?status=FAILED")

        assert response.status_code == 200
        results = response.json()["data"]["results"]
        assert all(r["status"] == "FAILED" for r in results)

    def test_filter_by_entity(self, auth_client):
        """?entity=GRN returns only GRN-typed logs."""
        outbox = _make_outbox(OutboxRecord.Status.SENT)
        _make_sync_log(outbox)

        client = auth_client("ADMIN")
        response = client.get("/api/pastel/sync-log/?entity=GRN")

        assert response.status_code == 200
        results = response.json()["data"]["results"]
        assert all(r["outbox"]["entity_type"] == "GRN" for r in results)


class TestResendOutbox:
    """POST /api/pastel/outbox/{id}/resend/ — requires IsAdmin."""

    def test_resend_failed_record(self, auth_client):
        """Admin can resend a FAILED OutboxRecord; it becomes SENT."""
        outbox = _make_outbox(OutboxRecord.Status.FAILED)
        _make_sync_log(outbox, PastelSyncLog.Status.FAILED)

        client = auth_client("ADMIN")
        response = client.post(f"/api/pastel/outbox/{outbox.pk}/resend/")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        outbox.refresh_from_db()
        assert outbox.status == OutboxRecord.Status.SENT

    def test_resend_abandoned_record(self, auth_client):
        """Admin can resend an ABANDONED record."""
        outbox = _make_outbox(OutboxRecord.Status.ABANDONED)

        client = auth_client("ADMIN")
        response = client.post(f"/api/pastel/outbox/{outbox.pk}/resend/")

        assert response.status_code == 200
        outbox.refresh_from_db()
        assert outbox.status == OutboxRecord.Status.SENT

    def test_resend_already_sent_returns_400(self, auth_client):
        """Resending an already-SENT record returns 400."""
        outbox = _make_outbox(OutboxRecord.Status.SENT)

        client = auth_client("ADMIN")
        response = client.post(f"/api/pastel/outbox/{outbox.pk}/resend/")

        assert response.status_code == 400
        assert response.json()["error"]["code"] == "ALREADY_SENT"

    def test_resend_nonexistent_returns_404(self, auth_client):
        """Resending a nonexistent record returns 404."""
        client = auth_client("ADMIN")
        response = client.post(f"/api/pastel/outbox/{uuid.uuid4()}/resend/")

        assert response.status_code == 404

    def test_non_admin_forbidden(self, auth_client):
        """Non-admin cannot resend records."""
        outbox = _make_outbox(OutboxRecord.Status.FAILED)
        client = auth_client("MANAGER")
        response = client.post(f"/api/pastel/outbox/{outbox.pk}/resend/")
        assert response.status_code == 403

    def test_anonymous_unauthorized(self, api_client):
        """Unauthenticated resend returns 401."""
        outbox = _make_outbox(OutboxRecord.Status.FAILED)
        response = api_client.post(f"/api/pastel/outbox/{outbox.pk}/resend/")
        assert response.status_code == 401


class TestReconciliation:
    """GET /api/pastel/reconciliation/ — requires IsAdmin or IsManager."""

    def test_admin_can_get_reconciliation(self, auth_client):
        """Admin sees the latest reconciliation run."""
        from apps.pastel.models import ReconciliationRun
        import datetime

        ReconciliationRun.objects.create(run_date=datetime.date.today())

        client = auth_client("ADMIN")
        response = client.get("/api/pastel/reconciliation/")

        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_manager_can_get_reconciliation(self, auth_client):
        """Manager sees the latest reconciliation run."""
        from apps.pastel.models import ReconciliationRun
        import datetime

        ReconciliationRun.objects.create(run_date=datetime.date.today())

        client = auth_client("MANAGER")
        response = client.get("/api/pastel/reconciliation/")

        assert response.status_code == 200

    def test_non_manager_non_admin_forbidden(self, auth_client):
        """Chef cannot access reconciliation."""
        client = auth_client("CHEF")
        response = client.get("/api/pastel/reconciliation/")
        assert response.status_code == 403

    def test_anonymous_unauthorized(self, api_client):
        """Unauthenticated request returns 401."""
        response = api_client.get("/api/pastel/reconciliation/")
        assert response.status_code == 401

    def test_no_runs_returns_404(self, auth_client):
        """When no runs exist, 404 is returned."""
        client = auth_client("ADMIN")
        response = client.get("/api/pastel/reconciliation/")
        assert response.status_code == 404

    def test_trigger_creates_new_run(self, auth_client, product, locations):
        """?trigger=1 creates a fresh reconciliation run and returns it."""
        from apps.inventory.services import MovementLine, post_movements
        import uuid as _uuid

        post_movements(
            document_type="GRN",
            document_id=_uuid.uuid4(),
            lines=[
                MovementLine(
                    product_id=product.pk,
                    location_id=locations["stores"].pk,
                    qty_delta=Decimal("5"),
                    movement_type="GRN_RECEIPT",
                )
            ],
        )

        client = auth_client("ADMIN")
        response = client.get("/api/pastel/reconciliation/?trigger=1")

        assert response.status_code == 200
        data = response.json()["data"]
        assert "run_date" in data
        assert "lines" in data
