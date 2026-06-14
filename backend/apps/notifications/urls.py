"""URL routes for notifications.

Mounted at /api/notifications/ by config/urls.py, giving:
  GET  /api/notifications/
  POST /api/notifications/<uuid:pk>/read/
"""

from django.urls import path

from apps.notifications.views import NotificationListView, NotificationReadView

urlpatterns = [
    path("", NotificationListView.as_view(), name="notification-list"),
    path("<uuid:pk>/read/", NotificationReadView.as_view(), name="notification-read"),
]
