"""Masterdata models: Category, Location, Product, Supplier."""

from django.db import models

from apps.core.models import BaseModel


class Category(BaseModel):
    """Product classification grouping (e.g. Dry Goods, Beverages)."""

    name = models.CharField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Category"
        verbose_name_plural = "Categories"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Location(BaseModel):
    """Physical storage or production location within the restaurant operation."""

    class Kind(models.TextChoices):
        STORES = "STORES", "Stores"
        KITCHEN = "KITCHEN", "Kitchen"
        UNIT = "UNIT", "Unit"

    name = models.CharField(max_length=100, unique=True)
    kind = models.CharField(max_length=10, choices=Kind.choices)

    class Meta:
        verbose_name = "Location"
        verbose_name_plural = "Locations"
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.kind})"


class Product(BaseModel):
    """Inventory product with unit-of-measure conversion factors and reorder level."""

    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=255)
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="products",
    )
    stock_uom = models.CharField(max_length=20)
    purchase_uom = models.CharField(max_length=20)
    recipe_uom = models.CharField(max_length=20)
    purchase_to_stock_factor = models.DecimalField(
        max_digits=12, decimal_places=6, default=1
    )
    recipe_to_stock_factor = models.DecimalField(
        max_digits=12, decimal_places=6, default=1
    )
    reorder_level = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    pastel_code = models.CharField(max_length=50, blank=True, default="")
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Product"
        verbose_name_plural = "Products"
        ordering = ["name"]
        indexes = [
            models.Index(fields=["category", "is_active"], name="product_cat_active_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.code} — {self.name}"


class Supplier(BaseModel):
    """External supplier record; deactivate-not-delete once on any PO."""

    class ApprovalStatus(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        SUSPENDED = "SUSPENDED", "Suspended"

    name = models.CharField(max_length=255)
    contact_name = models.CharField(max_length=255, blank=True, default="")
    email = models.EmailField(null=True, blank=True)
    phone = models.CharField(max_length=50, blank=True, default="")
    approval_status = models.CharField(
        max_length=10,
        choices=ApprovalStatus.choices,
        default=ApprovalStatus.APPROVED,
    )
    payment_terms = models.CharField(max_length=100, blank=True, default="")
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Supplier"
        verbose_name_plural = "Suppliers"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name
