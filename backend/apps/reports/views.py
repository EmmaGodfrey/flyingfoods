"""Report API views — one APIView per report endpoint.

All views are GET-only. Business logic lives in selectors.py; the export
layer lives in services.py. Views are deliberately thin: parse params,
call selector, call render_report.
"""

from rest_framework.request import Request
from rest_framework.views import APIView

from apps.reports.services import render_report
from apps.users.permissions import IsAdmin, IsManager, IsProcurementStaff, IsStockViewer


# ---------------------------------------------------------------------------
# Stock on hand
# ---------------------------------------------------------------------------


class StockOnHandView(APIView):
    """GET /api/reports/stock-on-hand/ — Stock Viewers and above."""

    permission_classes = [IsStockViewer]

    def get(self, request: Request):
        """Return current on-hand balances, optionally filtered by location.

        Query params:
            location (str): Optional location UUID to filter results.
            format (str): ``json`` (default), ``xlsx``, or ``pdf``.
        """
        from apps.reports.selectors import stock_on_hand

        location_id = request.query_params.get("location")
        rows = stock_on_hand(location_id=location_id)
        return render_report(rows, request, "Stock On Hand")


# ---------------------------------------------------------------------------
# Budget vs actual
# ---------------------------------------------------------------------------


class BudgetVsActualView(APIView):
    """GET /api/reports/budget-vs-actual/ — Managers only."""

    permission_classes = [IsManager]

    def get(self, request: Request):
        """Compare budget estimates to GRN actuals and wastage for a period.

        Query params:
            date_from (str): ISO date, inclusive lower bound.
            date_to (str): ISO date, inclusive upper bound.
            format (str): ``json`` (default), ``xlsx``, or ``pdf``.
        """
        from apps.reports.selectors import budget_vs_actual

        rows = budget_vs_actual(
            date_from=request.query_params.get("date_from"),
            date_to=request.query_params.get("date_to"),
        )
        return render_report(rows, request, "Budget vs Actual")


# ---------------------------------------------------------------------------
# PO register
# ---------------------------------------------------------------------------


class PORegisterView(APIView):
    """GET /api/reports/po-register/ — Procurement Staff."""

    permission_classes = [IsProcurementStaff]

    def get(self, request: Request):
        """Return a flat list of purchase orders with optional filters.

        Query params:
            supplier (str): Optional supplier UUID.
            date_from (str): ISO date filter on created_at.
            date_to (str): ISO date filter on created_at.
            format (str): ``json`` (default), ``xlsx``, or ``pdf``.
        """
        from apps.reports.selectors import po_register

        rows = po_register(
            supplier_id=request.query_params.get("supplier"),
            date_from=request.query_params.get("date_from"),
            date_to=request.query_params.get("date_to"),
        )
        return render_report(rows, request, "PO Register")


# ---------------------------------------------------------------------------
# GRN register
# ---------------------------------------------------------------------------


class GRNRegisterView(APIView):
    """GET /api/reports/grn-register/ — Procurement Staff."""

    permission_classes = [IsProcurementStaff]

    def get(self, request: Request):
        """Return a flat list of posted GRNs with optional date filter.

        Query params:
            date_from (str): ISO date filter on created_at.
            date_to (str): ISO date filter on created_at.
            format (str): ``json`` (default), ``xlsx``, or ``pdf``.
        """
        from apps.reports.selectors import grn_register

        rows = grn_register(
            date_from=request.query_params.get("date_from"),
            date_to=request.query_params.get("date_to"),
        )
        return render_report(rows, request, "GRN Register")


# ---------------------------------------------------------------------------
# Issues by destination
# ---------------------------------------------------------------------------


class IssuesByDestinationView(APIView):
    """GET /api/reports/issues-by-destination/ — Managers only."""

    permission_classes = [IsManager]

    def get(self, request: Request):
        """Return count and value of ISSUE_IN movements grouped by location.

        Query params:
            format (str): ``json`` (default), ``xlsx``, or ``pdf``.
        """
        from apps.reports.selectors import issues_by_destination

        rows = issues_by_destination()
        return render_report(rows, request, "Issues by Destination")


# ---------------------------------------------------------------------------
# Wastage report
# ---------------------------------------------------------------------------


class WastageReportView(APIView):
    """GET /api/reports/wastage/ — Managers only."""

    permission_classes = [IsManager]

    def get(self, request: Request):
        """Return wastage totals grouped by a chosen dimension.

        Query params:
            by (str): One of ``reason`` (default), ``item``, ``location``, ``user``.
            format (str): ``json`` (default), ``xlsx``, or ``pdf``.
        """
        from apps.reports.selectors import wastage_report

        by = request.query_params.get("by", "reason")
        rows = wastage_report(by=by)
        return render_report(rows, request, f"Wastage by {by.capitalize()}")


# ---------------------------------------------------------------------------
# Service time
# ---------------------------------------------------------------------------


class ServiceTimeView(APIView):
    """GET /api/reports/service-time/ — Managers only."""

    permission_classes = [IsManager]

    def get(self, request: Request):
        """Return average and median kitchen service durations.

        Query params:
            format (str): ``json`` (default), ``xlsx``, or ``pdf``.
        """
        from apps.reports.selectors import service_time

        rows = service_time()
        return render_report(rows, request, "Service Time")


# ---------------------------------------------------------------------------
# Movers
# ---------------------------------------------------------------------------


class MoversView(APIView):
    """GET /api/reports/movers/ — Managers only."""

    permission_classes = [IsManager]

    def get(self, request: Request):
        """Return products ranked by SALE_DEDUCTION quantity over the period.

        Query params:
            period (int): Number of days to look back (default 30).
            format (str): ``json`` (default), ``xlsx``, or ``pdf``.
        """
        from apps.reports.selectors import movers

        period_str = request.query_params.get("period", "30")
        try:
            period_days = int(period_str)
        except (TypeError, ValueError):
            period_days = 30

        rows = movers(period_days=period_days)
        return render_report(rows, request, "Fast/Slow Movers")


# ---------------------------------------------------------------------------
# Leakage
# ---------------------------------------------------------------------------


class LeakageView(APIView):
    """GET /api/reports/leakage/ — Managers only."""

    permission_classes = [IsManager]

    def get(self, request: Request):
        """Return per-product consumption gap (theoretical vs actual).

        Query params:
            date_from (str): ISO date, inclusive lower bound.
            date_to (str): ISO date, inclusive upper bound.
            format (str): ``json`` (default), ``xlsx``, or ``pdf``.
        """
        from apps.reports.selectors import leakage

        rows = leakage(
            date_from=request.query_params.get("date_from"),
            date_to=request.query_params.get("date_to"),
        )
        return render_report(rows, request, "Leakage Report")


# ---------------------------------------------------------------------------
# Recipe costing
# ---------------------------------------------------------------------------


class RecipeCostingView(APIView):
    """GET /api/reports/recipe-costing/ — Managers only."""

    permission_classes = [IsManager]

    def get(self, request: Request):
        """Return plate cost and gross margin per published menu item.

        Query params:
            format (str): ``json`` (default), ``xlsx``, or ``pdf``.
        """
        from apps.reports.selectors import recipe_costing

        rows = recipe_costing()
        return render_report(rows, request, "Recipe Costing")


# ---------------------------------------------------------------------------
# Reorder suggestions
# ---------------------------------------------------------------------------


class ReorderSuggestionsView(APIView):
    """GET /api/reports/reorder-suggestions/ — Stock Viewers and above."""

    permission_classes = [IsStockViewer]

    def get(self, request: Request):
        """Return products at/below reorder level with suggested qty and velocity.

        Query params:
            format (str): ``json`` (default), ``xlsx``, or ``pdf``.
        """
        from apps.reports.selectors import reorder_suggestions

        rows = reorder_suggestions()
        return render_report(rows, request, "Reorder Suggestions")


# ---------------------------------------------------------------------------
# Pastel reconciliation — lazy import; degrades gracefully
# ---------------------------------------------------------------------------


class PastelReconciliationView(APIView):
    """GET /api/reports/pastel-reconciliation/ — Admins and Managers."""

    permission_classes = [IsAdmin | IsManager]

    def get(self, request: Request):
        """Return the latest Pastel reconciliation run result.

        Falls back to an empty list when the ``apps.pastel`` reconciliation
        module has not been implemented yet.

        Query params:
            format (str): ``json`` (default), ``xlsx``, or ``pdf``.
        """
        try:
            from apps.pastel.selectors import latest_reconciliation  # type: ignore[import]

            rows = latest_reconciliation()
        except (ImportError, AttributeError):
            rows = []

        return render_report(rows, request, "Pastel Reconciliation")
