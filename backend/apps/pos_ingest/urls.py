"""POS ingestion routes, mounted at /api/pos/ by config/urls.py."""

from django.urls import path

from apps.pos_ingest.views import (
    SaleEventIngestView,
    SaleEventListView,
    SaleEventReplayView,
)

urlpatterns = [
    path("sale-events/", SaleEventListView.as_view(), name="sale-event-list"),
    path("sale-events/ingest/", SaleEventIngestView.as_view(), name="sale-event-ingest"),
    path("sale-events/<uuid:pk>/replay/", SaleEventReplayView.as_view(), name="sale-event-replay"),
]
