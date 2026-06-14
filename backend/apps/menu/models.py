"""Versioned menu items and recipes with effective dating."""

import datetime
from typing import Optional

from django.db import models

from apps.core.exceptions import ImmutableVersionError
from apps.core.models import BaseModel
from apps.masterdata.models import Product


class MenuItem(BaseModel):
    """Sellable item; `pos_code` maps POS sale lines onto our catalogue."""

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        INACTIVE = "INACTIVE", "Inactive"

    name = models.CharField(max_length=255)
    category = models.CharField(max_length=100, blank=True, default="")
    pos_code = models.CharField(max_length=50, unique=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE)
    schedule = models.JSONField(
        null=True,
        blank=True,
        help_text="Optional availability windows: [{'days': ['MON'], 'from': '11:00', 'to': '15:00'}]",
    )

    class Meta:
        verbose_name = "Menu Item"
        verbose_name_plural = "Menu Items"
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.pos_code})"


class RecipeVersion(BaseModel):
    """A point-in-time recipe; published versions are immutable."""

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        REVIEW = "REVIEW", "In review"
        PUBLISHED = "PUBLISHED", "Published"
        RETIRED = "RETIRED", "Retired"

    menu_item = models.ForeignKey(
        MenuItem, on_delete=models.PROTECT, related_name="recipe_versions"
    )
    version_no = models.PositiveIntegerField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    effective_from = models.DateField(null=True, blank=True)
    effective_to = models.DateField(null=True, blank=True)
    selling_price_snapshot = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )

    class Meta:
        verbose_name = "Recipe Version"
        verbose_name_plural = "Recipe Versions"
        constraints = [
            models.UniqueConstraint(
                fields=["menu_item", "version_no"], name="unique_version_per_item"
            )
        ]
        ordering = ["menu_item", "-version_no"]

    def __str__(self) -> str:
        return f"{self.menu_item.name} v{self.version_no} ({self.status})"

    def save(self, *args, **kwargs) -> None:
        """Block edits to published rows except the controlled retire transition."""
        if not self._state.adding:
            current = RecipeVersion.objects.filter(pk=self.pk).values(
                "status", "effective_to"
            ).first()
            if current and current["status"] == self.Status.PUBLISHED:
                retiring = (
                    self.status == self.Status.RETIRED
                    or current["effective_to"] != self.effective_to
                )
                if not retiring:
                    raise ImmutableVersionError()
        super().save(*args, **kwargs)

    @classmethod
    def active_for(
        cls, menu_item_id: object, on_date: Optional[datetime.date] = None
    ) -> Optional["RecipeVersion"]:
        """Return the published version effective on a date (default today)."""
        on_date = on_date or datetime.date.today()
        return (
            cls.objects.filter(
                menu_item_id=menu_item_id,
                status=cls.Status.PUBLISHED,
                effective_from__lte=on_date,
            )
            .filter(models.Q(effective_to__isnull=True) | models.Q(effective_to__gt=on_date))
            .order_by("-version_no")
            .first()
        )


class RecipeLine(BaseModel):
    """One ingredient line in a recipe version, quantified in the recipe UoM."""

    recipe_version = models.ForeignKey(
        RecipeVersion, on_delete=models.CASCADE, related_name="lines"
    )
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    qty_per_serving = models.DecimalField(max_digits=12, decimal_places=3)

    class Meta:
        verbose_name = "Recipe Line"
        verbose_name_plural = "Recipe Lines"
        constraints = [
            models.UniqueConstraint(
                fields=["recipe_version", "product"], name="unique_product_per_version"
            )
        ]

    def __str__(self) -> str:
        return f"{self.product.code} x {self.qty_per_serving}"
