"""URL patterns for the inventory app."""

from django.urls import path

from apps.inventory.views import (
    IssueNoteCreateView,
    IssueNotePostView,
    StockBalanceListView,
    StockMovementListView,
    StockTakeCreateView,
    StockTakeLinesUpdateView,
    StockTakePostView,
    TransferCreateView,
    TransferPostView,
)

urlpatterns = [
    path("stock/balances/", StockBalanceListView.as_view(), name="stock-balances"),
    path("stock/movements/", StockMovementListView.as_view(), name="stock-movements"),
    path("issues/", IssueNoteCreateView.as_view(), name="issue-notes"),
    path("issues/<uuid:pk>/post/", IssueNotePostView.as_view(), name="issue-notes-post"),
    path("transfers/", TransferCreateView.as_view(), name="transfers"),
    path("transfers/<uuid:pk>/post/", TransferPostView.as_view(), name="transfers-post"),
    path("stock-takes/", StockTakeCreateView.as_view(), name="stock-takes"),
    path("stock-takes/<uuid:pk>/lines/", StockTakeLinesUpdateView.as_view(), name="stock-takes-lines"),
    path("stock-takes/<uuid:pk>/post/", StockTakePostView.as_view(), name="stock-takes-post"),
]
