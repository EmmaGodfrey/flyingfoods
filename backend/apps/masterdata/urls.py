"""URL routes for masterdata resources.

Mounted under /api/ by config/urls.py, so the effective paths are:
  /api/products/
  /api/products/<uuid:pk>/
  /api/suppliers/
  /api/suppliers/<uuid:pk>/
  /api/locations/
"""

import uuid

from django.urls import path

from apps.masterdata.views import (
    LocationListView,
    ProductDetailView,
    ProductListCreateView,
    SupplierDetailView,
    SupplierListCreateView,
)

urlpatterns = [
    path("products/", ProductListCreateView.as_view(), name="product-list"),
    path("products/<uuid:pk>/", ProductDetailView.as_view(), name="product-detail"),
    path("suppliers/", SupplierListCreateView.as_view(), name="supplier-list"),
    path("suppliers/<uuid:pk>/", SupplierDetailView.as_view(), name="supplier-detail"),
    path("locations/", LocationListView.as_view(), name="location-list"),
]
