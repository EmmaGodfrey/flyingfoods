"""URL patterns for the Pastel integration API.

Mounted at /api/pastel/ by config/urls.py.
"""

from django.urls import path

from apps.pastel.views import ReconciliationView, ResendOutboxView, SyncLogListView

urlpatterns = [
    path("sync-log/", SyncLogListView.as_view(), name="pastel-sync-log"),
    path("outbox/<uuid:pk>/resend/", ResendOutboxView.as_view(), name="pastel-resend"),
    path("reconciliation/", ReconciliationView.as_view(), name="pastel-reconciliation"),
]
