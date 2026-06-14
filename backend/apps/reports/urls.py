"""URL patterns for the reports app.

All paths are mounted under /api/reports/ by config/urls.py.
"""

from django.urls import path

from apps.reports.views import (
    BudgetVsActualView,
    GRNRegisterView,
    IssuesByDestinationView,
    LeakageView,
    MoversView,
    PORegisterView,
    PastelReconciliationView,
    RecipeCostingView,
    ReorderSuggestionsView,
    ServiceTimeView,
    StockOnHandView,
    WastageReportView,
)

urlpatterns = [
    path("stock-on-hand/", StockOnHandView.as_view(), name="report-stock-on-hand"),
    path("budget-vs-actual/", BudgetVsActualView.as_view(), name="report-budget-vs-actual"),
    path("po-register/", PORegisterView.as_view(), name="report-po-register"),
    path("grn-register/", GRNRegisterView.as_view(), name="report-grn-register"),
    path("issues-by-destination/", IssuesByDestinationView.as_view(), name="report-issues-by-destination"),
    path("wastage/", WastageReportView.as_view(), name="report-wastage"),
    path("service-time/", ServiceTimeView.as_view(), name="report-service-time"),
    path("movers/", MoversView.as_view(), name="report-movers"),
    path("leakage/", LeakageView.as_view(), name="report-leakage"),
    path("recipe-costing/", RecipeCostingView.as_view(), name="report-recipe-costing"),
    path("reorder-suggestions/", ReorderSuggestionsView.as_view(), name="report-reorder-suggestions"),
    path("pastel-reconciliation/", PastelReconciliationView.as_view(), name="report-pastel-reconciliation"),
]
