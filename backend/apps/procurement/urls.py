"""Procurement URL patterns."""

from django.urls import path

from apps.procurement.views import (
    BudgetCreateView,
    BudgetListView,
    BudgetSubmitView,
    GRNCreateView,
    InvoiceCreateView,
    InvoiceMatchDisputeView,
    InvoiceMatchEscalateView,
    InvoiceMatchResolveView,
    PurchaseOrderCreateView,
    PurchaseOrderListView,
    PurchaseOrderPdfView,
    PurchaseOrderSendView,
    SupplierHistoryView,
)

urlpatterns = [
    # Budgets
    path("budgets/", BudgetListView.as_view(), name="budget-list"),
    path("budgets/create/", BudgetCreateView.as_view(), name="budget-create"),
    path("budgets/<uuid:pk>/submit/", BudgetSubmitView.as_view(), name="budget-submit"),
    # Purchase Orders
    path("purchase-orders/", PurchaseOrderListView.as_view(), name="po-list"),
    path("purchase-orders/create/", PurchaseOrderCreateView.as_view(), name="po-create"),
    path("purchase-orders/<uuid:pk>/send/", PurchaseOrderSendView.as_view(), name="po-send"),
    path("purchase-orders/<uuid:pk>/pdf/", PurchaseOrderPdfView.as_view(), name="po-pdf"),
    path("purchase-orders/<uuid:pk>/grns/", GRNCreateView.as_view(), name="grn-create"),
    path("purchase-orders/<uuid:pk>/invoices/", InvoiceCreateView.as_view(), name="invoice-create"),
    # Invoice matches
    path(
        "invoice-matches/<uuid:pk>/resolve/",
        InvoiceMatchResolveView.as_view(),
        name="invoice-match-resolve",
    ),
    path(
        "invoice-matches/<uuid:pk>/dispute/",
        InvoiceMatchDisputeView.as_view(),
        name="invoice-match-dispute",
    ),
    path(
        "invoice-matches/<uuid:pk>/escalate/",
        InvoiceMatchEscalateView.as_view(),
        name="invoice-match-escalate",
    ),
    # Supplier history
    path("supplier-history/<uuid:pk>/", SupplierHistoryView.as_view(), name="supplier-history"),
]
