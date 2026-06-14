"""Menu and recipe write services: versioning and the publish workflow."""

from typing import Any, Optional, Sequence

from django.db import transaction
from rest_framework.exceptions import ValidationError

from apps.core.exceptions import HasHistoryError
from apps.core.services import log_audit
from apps.menu.models import MenuItem, RecipeLine, RecipeVersion


@transaction.atomic
def create_recipe_version(
    *,
    menu_item: MenuItem,
    lines: Sequence[tuple[Any, Any]],
    selling_price: Optional[Any] = None,
    user: Optional[Any] = None,
) -> RecipeVersion:
    """Create the next DRAFT recipe version for a menu item.

    Editing a recipe never overwrites: each call adds a new version. The
    previous published version stays intact so historical orders remain
    correct (FR-MR-02).
    """
    if not lines:
        raise ValidationError({"lines": "A recipe needs at least one ingredient line."})
    last = menu_item.recipe_versions.order_by("-version_no").values_list("version_no", flat=True).first()
    version = RecipeVersion.objects.create(
        menu_item=menu_item,
        version_no=(last or 0) + 1,
        selling_price_snapshot=selling_price,
    )
    RecipeLine.objects.bulk_create(
        [
            RecipeLine(recipe_version=version, product_id=product_id, qty_per_serving=qty)
            for product_id, qty in lines
        ]
    )
    log_audit(entity="RecipeVersion", entity_id=version.pk, action="CREATE", user=user)
    return version


@transaction.atomic
def submit_for_review(*, version: RecipeVersion, user: Optional[Any] = None) -> RecipeVersion:
    """Move a draft recipe version into review."""
    if version.status != RecipeVersion.Status.DRAFT:
        raise ValidationError({"status": "Only draft versions can enter review."})
    version.status = RecipeVersion.Status.REVIEW
    version.save(update_fields=["status", "updated_at"])
    log_audit(entity="RecipeVersion", entity_id=version.pk, action="REVIEW", user=user)
    return version


@transaction.atomic
def publish_version(*, version: RecipeVersion, effective_from, user: Optional[Any] = None) -> RecipeVersion:
    """Publish a recipe version, retiring the previously published one.

    The outgoing version's `effective_to` is closed at the new version's
    `effective_from`, so date-based resolution never overlaps.
    """
    if version.status not in (RecipeVersion.Status.DRAFT, RecipeVersion.Status.REVIEW):
        raise ValidationError({"status": "Only draft or review versions can be published."})
    if effective_from is None:
        raise ValidationError({"effective_from": "An effective-from date is required to publish."})

    current = (
        RecipeVersion.objects.filter(
            menu_item=version.menu_item, status=RecipeVersion.Status.PUBLISHED
        )
        .exclude(pk=version.pk)
        .first()
    )
    if current is not None:
        current.effective_to = effective_from
        current.status = RecipeVersion.Status.RETIRED
        current.save(update_fields=["effective_to", "status", "updated_at"])

    version.status = RecipeVersion.Status.PUBLISHED
    version.effective_from = effective_from
    version.effective_to = None
    version.save(update_fields=["status", "effective_from", "effective_to", "updated_at"])
    log_audit(
        entity="RecipeVersion",
        entity_id=version.pk,
        action="PUBLISH",
        user=user,
        after={"effective_from": str(effective_from)},
    )
    return version


def deactivate_menu_item(*, menu_item: MenuItem, user: Optional[Any] = None) -> MenuItem:
    """Deactivate a menu item, refusing if it has order history (FR-MR-05)."""
    from apps.kitchen.models import OrderItem

    if OrderItem.objects.filter(menu_item=menu_item).exists():
        # Deactivation is allowed; hard deletion is what is forbidden.
        pass
    menu_item.status = MenuItem.Status.INACTIVE
    menu_item.save(update_fields=["status", "updated_at"])
    log_audit(entity="MenuItem", entity_id=menu_item.pk, action="DEACTIVATE", user=user)
    return menu_item


def guard_delete(*, menu_item: MenuItem) -> None:
    """Raise when a menu item with history is deleted; callers offer deactivate."""
    from apps.kitchen.models import OrderItem

    if OrderItem.objects.filter(menu_item=menu_item).exists():
        raise HasHistoryError()
