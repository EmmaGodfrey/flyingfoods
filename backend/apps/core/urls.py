"""URL routes for core configuration and approval resources.

Mounted under /api/ by config/urls.py, giving effective paths:
  /api/reason-codes/
  /api/reason-codes/<uuid:pk>/
  /api/thresholds/
  /api/thresholds/<uuid:pk>/
  /api/integration-settings/
  /api/integration-health/
  /api/approvals/
  /api/approvals/<uuid:pk>/approve/
  /api/approvals/<uuid:pk>/reject/
  /api/approvals/<uuid:pk>/investigate/
"""

from django.urls import path

from apps.core.views import (
    ApprovalApproveView,
    ApprovalInvestigateView,
    ApprovalListView,
    ApprovalRejectView,
    HealthView,
    IntegrationHealthView,
    IntegrationSettingsListView,
    ReasonCodeDetailView,
    ReasonCodeListCreateView,
    ThresholdConfigDetailView,
    ThresholdConfigListCreateView,
)

urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
    # Reason codes
    path("reason-codes/", ReasonCodeListCreateView.as_view(), name="reason-code-list"),
    path("reason-codes/<uuid:pk>/", ReasonCodeDetailView.as_view(), name="reason-code-detail"),
    # Thresholds
    path("thresholds/", ThresholdConfigListCreateView.as_view(), name="threshold-list"),
    path("thresholds/<uuid:pk>/", ThresholdConfigDetailView.as_view(), name="threshold-detail"),
    # Integration settings — one view handles GET list and PUT upsert
    path("integration-settings/", IntegrationSettingsListView.as_view(), name="integration-settings"),
    # Integration health
    path("integration-health/", IntegrationHealthView.as_view(), name="integration-health"),
    # Approvals
    path("approvals/", ApprovalListView.as_view(), name="approval-list"),
    path("approvals/<uuid:pk>/approve/", ApprovalApproveView.as_view(), name="approval-approve"),
    path("approvals/<uuid:pk>/reject/", ApprovalRejectView.as_view(), name="approval-reject"),
    path("approvals/<uuid:pk>/investigate/", ApprovalInvestigateView.as_view(), name="approval-investigate"),
]
