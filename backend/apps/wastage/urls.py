"""Wastage routes, mounted under /api/ by config/urls.py."""

from django.urls import path

from apps.wastage.views import WastageListCreateView

urlpatterns = [
    path("wastage/", WastageListCreateView.as_view(), name="wastage-list"),
]
