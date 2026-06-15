"""Views for masterdata: products, suppliers, locations.

All business logic (future: category/supplier creation side-effects) belongs in
services.py. These views stay thin: permission check, serializer, response.
"""

from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from apps.users.permissions import IsAdmin, IsProcurementStaff

from apps.masterdata.filters import ProductFilter, SupplierFilter
from apps.masterdata.models import Location, Product, Supplier
from apps.masterdata.serializers import (
    LocationSerializer,
    ProductListSerializer,
    ProductSerializer,
    SupplierSerializer,
)


class ProductListCreateView(generics.ListCreateAPIView):
    """GET /products/ — any authenticated; POST /products/ — ADMIN only."""

    filterset_class = ProductFilter
    ordering_fields = ["name", "code", "created_at"]
    ordering = ["name"]

    def get_queryset(self):
        """Return all products with category pre-fetched."""
        return Product.objects.select_related("category").order_by("name")

    def get_serializer_class(self):
        """Use compact serializer for list, full for create."""
        if self.request.method == "GET":
            return ProductListSerializer
        return ProductSerializer

    def get_permissions(self):
        """Any authenticated user may list; only ADMIN may create."""
        if self.request.method == "GET":
            return [IsAuthenticated()]
        return [IsAdmin()]


class ProductDetailView(generics.RetrieveUpdateAPIView):
    """GET /products/{id}/ — any authenticated; PATCH /products/{id}/ — ADMIN only."""

    serializer_class = ProductSerializer
    queryset = Product.objects.select_related("category")
    http_method_names = ["get", "patch", "head", "options"]

    def get_permissions(self):
        """Any authenticated user may retrieve; only ADMIN may update."""
        if self.request.method == "GET":
            return [IsAuthenticated()]
        return [IsAdmin()]


class SupplierListCreateView(generics.ListCreateAPIView):
    """GET /suppliers/ — ProcurementStaff+; POST /suppliers/ — ADMIN only."""

    serializer_class = SupplierSerializer
    filterset_class = SupplierFilter
    ordering_fields = ["name", "created_at"]
    ordering = ["name"]

    def get_queryset(self):
        """Return all suppliers ordered by name."""
        return Supplier.objects.order_by("name")

    def get_permissions(self):
        """ProcurementStaff may list; only ADMIN may create."""
        if self.request.method == "GET":
            return [IsProcurementStaff()]
        return [IsAdmin()]


class SupplierDetailView(generics.RetrieveUpdateAPIView):
    """GET/PATCH /suppliers/{id}/ — procurement read, ADMIN write."""

    serializer_class = SupplierSerializer
    queryset = Supplier.objects.all()
    http_method_names = ["get", "patch", "head", "options"]

    def get_permissions(self):
        """ProcurementStaff may retrieve; only ADMIN may update."""
        if self.request.method == "GET":
            return [IsProcurementStaff()]
        return [IsAdmin()]


class LocationListView(generics.ListAPIView):
    """GET /locations/ — any authenticated user."""

    serializer_class = LocationSerializer
    queryset = Location.objects.order_by("name")
    permission_classes = [IsAuthenticated]
