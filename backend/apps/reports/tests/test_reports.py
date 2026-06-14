"""Tests for the reports module.

Seeds minimal data using apps.inventory.services.post_movements, then
exercises the key report endpoints and export formats.

Fixtures `product`, `locations`, `auth_client`, `make_user` come from
the root conftest.py.
"""

import uuid
from decimal import Decimal

import pytest

from apps.inventory.models import StockMovement
from apps.inventory.services import MovementLine, post_movements
from apps.users.models import User

pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _receipt(product, location, qty: Decimal, unit_cost: Decimal = Decimal("5.00")):
    """Post a GRN_RECEIPT movement."""
    return post_movements(
        document_type="GRN",
        document_id=uuid.uuid4(),
        lines=[
            MovementLine(
                product_id=product.pk,
                location_id=location.pk,
                qty_delta=qty,
                movement_type=StockMovement.MovementType.GRN_RECEIPT,
                unit_cost=unit_cost,
            )
        ],
    )


def _sale(product, location, qty: Decimal):
    """Post a SALE_DEDUCTION movement (absolute qty, stored as negative delta)."""
    return post_movements(
        document_type="SALE",
        document_id=uuid.uuid4(),
        lines=[
            MovementLine(
                product_id=product.pk,
                location_id=location.pk,
                qty_delta=-qty,
                movement_type=StockMovement.MovementType.SALE_DEDUCTION,
                unit_cost=None,
            )
        ],
        allow_negative=True,
    )


# ---------------------------------------------------------------------------
# Stock on hand
# ---------------------------------------------------------------------------


class TestStockOnHand:
    """Tests for GET /api/reports/stock-on-hand/."""

    def test_returns_rows_and_flags_below_reorder(self, auth_client, product, locations):
        """Rows include a below_reorder boolean computed from on-hand vs reorder_level."""
        # product has reorder_level=10; receipt of 5 → below_reorder=True
        _receipt(product, locations["stores"], Decimal("5"))

        client = auth_client(User.Role.MANAGER)
        response = client.get("/api/reports/stock-on-hand/")

        assert response.status_code == 200
        data = response.json()
        # Envelope wraps payload in {"success": true, "data": [...]}
        rows = data["data"]
        assert len(rows) >= 1
        row = next(r for r in rows if r["product_code"] == product.code)
        assert row["below_reorder"] is True

    def test_below_reorder_false_when_stock_sufficient(self, auth_client, product, locations):
        """When on-hand exceeds reorder_level, below_reorder is False."""
        _receipt(product, locations["stores"], Decimal("50"))

        client = auth_client(User.Role.MANAGER)
        response = client.get("/api/reports/stock-on-hand/")
        data = response.json()
        rows = data["data"]
        row = next(r for r in rows if r["product_code"] == product.code)
        assert row["below_reorder"] is False

    def test_location_filter_narrows_results(self, auth_client, product, locations):
        """Providing ?location= restricts results to that location."""
        _receipt(product, locations["stores"], Decimal("20"))
        _receipt(product, locations["kitchen"], Decimal("15"))

        client = auth_client(User.Role.STOREKEEPER)
        kitchen_id = str(locations["kitchen"].pk)
        response = client.get(f"/api/reports/stock-on-hand/?location={kitchen_id}")
        assert response.status_code == 200
        rows = response.json()["data"]
        location_names = {r["location"] for r in rows}
        assert location_names == {"Kitchen"}

    def test_anon_is_rejected(self, api_client):
        """Unauthenticated requests receive a 401."""
        response = api_client.get("/api/reports/stock-on-hand/")
        assert response.status_code == 401

    def test_waiter_is_forbidden(self, auth_client):
        """Waiters do not have the StockViewer permission."""
        client = auth_client(User.Role.WAITER)
        response = client.get("/api/reports/stock-on-hand/")
        assert response.status_code == 403


# ---------------------------------------------------------------------------
# XLSX export
# ---------------------------------------------------------------------------


class TestXlsxExport:
    """XLSX export returns the correct MIME type and non-empty body."""

    def test_xlsx_export_content_type(self, auth_client, product, locations):
        """?format=xlsx returns application/vnd.openxmlformats-officedocument… content type."""
        _receipt(product, locations["stores"], Decimal("20"))

        client = auth_client(User.Role.MANAGER)
        response = client.get("/api/reports/stock-on-hand/?format=xlsx")

        assert response.status_code == 200
        assert (
            response["Content-Type"]
            == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        assert len(response.content) > 0

    def test_xlsx_export_has_attachment_header(self, auth_client, product, locations):
        """XLSX response carries a Content-Disposition attachment header."""
        _receipt(product, locations["stores"], Decimal("10"))

        client = auth_client(User.Role.MANAGER)
        response = client.get("/api/reports/stock-on-hand/?format=xlsx")

        assert "attachment" in response.get("Content-Disposition", "")


# ---------------------------------------------------------------------------
# Service time — permission gate
# ---------------------------------------------------------------------------


class TestServiceTimePermissions:
    """Service time is a Manager-only endpoint."""

    def test_manager_can_access(self, auth_client):
        """A Manager receives a 200 response from the service-time endpoint."""
        client = auth_client(User.Role.MANAGER)
        response = client.get("/api/reports/service-time/")
        assert response.status_code == 200

    def test_waiter_is_forbidden(self, auth_client):
        """A Waiter receives a 403 on the Manager-only service-time endpoint."""
        client = auth_client(User.Role.WAITER)
        response = client.get("/api/reports/service-time/")
        assert response.status_code == 403

    def test_anon_is_rejected(self, api_client):
        """Unauthenticated requests receive a 401."""
        response = api_client.get("/api/reports/service-time/")
        assert response.status_code == 401

    def test_returns_list_payload(self, auth_client):
        """Service-time response data is a list (even when no orders exist)."""
        client = auth_client(User.Role.MANAGER)
        response = client.get("/api/reports/service-time/")
        assert isinstance(response.json()["data"], list)


# ---------------------------------------------------------------------------
# Movers
# ---------------------------------------------------------------------------


class TestMovers:
    """Movers report returns 200 with a list payload."""

    def test_movers_returns_200(self, auth_client, product, locations):
        """Movers endpoint responds with 200 for a Manager."""
        _receipt(product, locations["stores"], Decimal("100"))
        _sale(product, locations["stores"], Decimal("30"))

        client = auth_client(User.Role.MANAGER)
        response = client.get("/api/reports/movers/")
        assert response.status_code == 200

    def test_movers_payload_is_list(self, auth_client, product, locations):
        """Movers data field is a list."""
        _receipt(product, locations["stores"], Decimal("50"))
        _sale(product, locations["stores"], Decimal("10"))

        client = auth_client(User.Role.MANAGER)
        response = client.get("/api/reports/movers/")
        assert isinstance(response.json()["data"], list)

    def test_movers_contains_sold_product(self, auth_client, product, locations):
        """A product with SALE_DEDUCTION movements appears in movers output."""
        _receipt(product, locations["stores"], Decimal("100"))
        _sale(product, locations["stores"], Decimal("25"))

        client = auth_client(User.Role.MANAGER)
        response = client.get("/api/reports/movers/")
        codes = [r["product_code"] for r in response.json()["data"]]
        assert product.code in codes


# ---------------------------------------------------------------------------
# Leakage
# ---------------------------------------------------------------------------


class TestLeakage:
    """Leakage report surfaces the gap between theoretical and actual consumption."""

    def test_leakage_returns_200(self, auth_client, product, locations):
        """Leakage endpoint responds with 200 for a Manager."""
        _receipt(product, locations["stores"], Decimal("100"))
        _sale(product, locations["stores"], Decimal("40"))

        client = auth_client(User.Role.MANAGER)
        response = client.get("/api/reports/leakage/")
        assert response.status_code == 200

    def test_leakage_payload_is_list(self, auth_client, product, locations):
        """Leakage data field is a list."""
        client = auth_client(User.Role.MANAGER)
        response = client.get("/api/reports/leakage/")
        assert isinstance(response.json()["data"], list)

    def test_leakage_product_appears_when_gap_exists(self, auth_client, product, locations):
        """Product with sale deduction and wastage movement shows a positive gap."""
        _receipt(product, locations["stores"], Decimal("100"))
        _sale(product, locations["stores"], Decimal("20"))

        # Post a WASTAGE movement to create a gap.
        post_movements(
            document_type="WASTAGE",
            document_id=uuid.uuid4(),
            lines=[
                MovementLine(
                    product_id=product.pk,
                    location_id=locations["stores"].pk,
                    qty_delta=Decimal("-5"),
                    movement_type=StockMovement.MovementType.WASTAGE,
                )
            ],
            allow_negative=True,
        )

        client = auth_client(User.Role.MANAGER)
        response = client.get("/api/reports/leakage/")
        rows = response.json()["data"]
        matching = [r for r in rows if r["product_code"] == product.code]
        assert matching, "Product should appear in leakage report"
        assert matching[0]["gap_qty"] > 0


# ---------------------------------------------------------------------------
# Reorder suggestions
# ---------------------------------------------------------------------------


class TestReorderSuggestions:
    """Reorder suggestions lists products at/below their reorder level."""

    def test_reorder_suggestions_returns_200(self, auth_client, product, locations):
        """Reorder suggestions endpoint responds with 200 for a Stock Viewer."""
        # Stock below reorder_level=10.
        _receipt(product, locations["stores"], Decimal("5"))

        client = auth_client(User.Role.STOREKEEPER)
        response = client.get("/api/reports/reorder-suggestions/")
        assert response.status_code == 200

    def test_reorder_suggestions_payload_is_list(self, auth_client, product, locations):
        """Reorder suggestions data field is a list."""
        client = auth_client(User.Role.STOREKEEPER)
        response = client.get("/api/reports/reorder-suggestions/")
        assert isinstance(response.json()["data"], list)

    def test_product_below_reorder_appears_in_suggestions(self, auth_client, product, locations):
        """A product with on-hand below reorder_level appears in suggestions."""
        # reorder_level=10; receipt of 3 → below reorder.
        _receipt(product, locations["stores"], Decimal("3"))

        client = auth_client(User.Role.STOREKEEPER)
        response = client.get("/api/reports/reorder-suggestions/")
        rows = response.json()["data"]
        codes = [r["product_code"] for r in rows]
        assert product.code in codes

    def test_product_above_reorder_absent_from_suggestions(self, auth_client, product, locations):
        """A product comfortably above reorder_level does not appear in suggestions."""
        # reorder_level=10; receipt of 100 → above reorder.
        _receipt(product, locations["stores"], Decimal("100"))

        client = auth_client(User.Role.STOREKEEPER)
        response = client.get("/api/reports/reorder-suggestions/")
        rows = response.json()["data"]
        codes = [r["product_code"] for r in rows]
        assert product.code not in codes


# ---------------------------------------------------------------------------
# Budget vs actual
# ---------------------------------------------------------------------------


class TestBudgetVsActual:
    """Budget vs actual endpoint is accessible to Managers."""

    def test_returns_200(self, auth_client):
        """Endpoint responds with 200 (empty list when no budgets exist)."""
        client = auth_client(User.Role.MANAGER)
        response = client.get("/api/reports/budget-vs-actual/")
        assert response.status_code == 200
        assert isinstance(response.json()["data"], list)

    def test_waiter_is_forbidden(self, auth_client):
        """Waiter role is rejected with 403."""
        client = auth_client(User.Role.WAITER)
        response = client.get("/api/reports/budget-vs-actual/")
        assert response.status_code == 403


# ---------------------------------------------------------------------------
# Issues by destination
# ---------------------------------------------------------------------------


class TestIssuesByDestination:
    """Issues-by-destination report groups ISSUE_IN movements."""

    def test_returns_200_with_list(self, auth_client, product, locations):
        """Endpoint responds with 200 and a list."""
        # First put stock into stores via a receipt.
        _receipt(product, locations["stores"], Decimal("10"))

        # Post an issue note: ISSUE_OUT from stores, ISSUE_IN to kitchen.
        post_movements(
            document_type="IssueNote",
            document_id=uuid.uuid4(),
            lines=[
                MovementLine(
                    product_id=product.pk,
                    location_id=locations["stores"].pk,
                    qty_delta=Decimal("-5"),
                    movement_type=StockMovement.MovementType.ISSUE_OUT,
                ),
                MovementLine(
                    product_id=product.pk,
                    location_id=locations["kitchen"].pk,
                    qty_delta=Decimal("5"),
                    movement_type=StockMovement.MovementType.ISSUE_IN,
                ),
            ],
        )

        client = auth_client(User.Role.MANAGER)
        response = client.get("/api/reports/issues-by-destination/")
        assert response.status_code == 200
        rows = response.json()["data"]
        assert isinstance(rows, list)
        kitchen_row = next((r for r in rows if r["location"] == "Kitchen"), None)
        assert kitchen_row is not None
        assert kitchen_row["count"] >= 1
