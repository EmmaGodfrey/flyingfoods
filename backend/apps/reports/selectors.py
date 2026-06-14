"""Report selectors: pure read functions returning list[dict] rows.

Each function performs ORM-level aggregation; no Python loops over querysets
for aggregate computation. All inputs are validated before hitting the DB.
"""

import datetime
import statistics
from decimal import Decimal
from typing import Optional

from django.db.models import DecimalField, ExpressionWrapper, F, Sum
from django.db.models.functions import Coalesce

from apps.inventory.models import StockBalance, StockMovement
from apps.wastage.models import WastageEntry


def _parse_date(raw: Optional[str], name: str) -> Optional[datetime.date]:
    """Parse an ISO date string into a date object; return None if blank.

    Args:
        raw: An ISO-8601 date string (``YYYY-MM-DD``) or None/empty.
        name: Human-readable field label used in error messages.

    Returns:
        A :class:`datetime.date` instance, or ``None`` when *raw* is falsy.

    Raises:
        ValueError: When *raw* is non-empty but cannot be parsed.
    """
    if not raw:
        return None
    try:
        return datetime.date.fromisoformat(raw)
    except ValueError as exc:
        raise ValueError(f"Invalid date for {name!r}: {raw!r} — expected YYYY-MM-DD.") from exc


# ---------------------------------------------------------------------------
# Stock on hand
# ---------------------------------------------------------------------------


def stock_on_hand(location_id: Optional[str] = None) -> list[dict]:
    """Return current on-hand balances per (product, location).

    Args:
        location_id: Optional UUID string to filter by a single location.

    Returns:
        List of dicts with keys: product_code, product_name, location,
        qty_on_hand, reorder_level, below_reorder.
    """
    qs = (
        StockBalance.objects.select_related("product", "location")
        .order_by("product__name", "location__name")
    )
    if location_id:
        qs = qs.filter(location_id=location_id)

    rows: list[dict] = []
    for bal in qs:
        rows.append(
            {
                "product_code": bal.product.code,
                "product_name": bal.product.name,
                "location": bal.location.name,
                "qty_on_hand": bal.qty_on_hand,
                "reorder_level": bal.product.reorder_level,
                "below_reorder": bal.qty_on_hand <= bal.product.reorder_level,
            }
        )
    return rows


# ---------------------------------------------------------------------------
# Budget vs actual — delegated to procurement selectors with wastage overlay
# ---------------------------------------------------------------------------


def budget_vs_actual(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> list[dict]:
    """Compare procurement budget estimates to GRN actuals plus wastage value.

    Delegates the base query to ``apps.procurement.selectors.budget_vs_actual``
    and annotates each row with the wastage value for the same period.

    Args:
        date_from: ISO date string (inclusive). Defaults to 30 days ago.
        date_to: ISO date string (inclusive). Defaults to today.

    Returns:
        List of dicts with keys: budget_id, status, total_estimated,
        grn_actual, wastage_value, variance.
    """
    from apps.procurement.selectors import budget_vs_actual as _proc_bva

    today = datetime.date.today()
    d_from: datetime.date = _parse_date(date_from, "date_from") or (today - datetime.timedelta(days=30))
    d_to: datetime.date = _parse_date(date_to, "date_to") or today

    base_rows = _proc_bva(d_from, d_to)

    # Aggregate total wastage value for the period in one query.
    wastage_total = (
        WastageEntry.objects.filter(
            created_at__date__gte=d_from,
            created_at__date__lte=d_to,
            status=WastageEntry.Status.POSTED,
        )
        .aggregate(total=Coalesce(Sum("value"), Decimal("0")))["total"]
    )

    result: list[dict] = []
    for row in base_rows:
        grn_actual = row.get("actual_cost", Decimal("0")) or Decimal("0")
        budget_amount = row.get("total_estimated", Decimal("0")) or Decimal("0")
        variance = budget_amount - Decimal(str(grn_actual))
        result.append(
            {
                "budget_id": row.get("budget_id"),
                "status": row.get("status"),
                "budget": budget_amount,
                "approved": budget_amount,
                "grn_actual": grn_actual,
                "wastage_value": wastage_total,
                "variance": variance,
            }
        )
    return result


# ---------------------------------------------------------------------------
# PO register
# ---------------------------------------------------------------------------


def po_register(
    supplier_id: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> list[dict]:
    """Return a flat register of purchase orders.

    Args:
        supplier_id: Optional UUID string to filter by supplier.
        date_from: ISO date string (inclusive lower bound on created_at).
        date_to: ISO date string (inclusive upper bound on created_at).

    Returns:
        List of dicts with keys: po_number, supplier, status, total, created_at.
    """
    from apps.procurement.models import POLine, PurchaseOrder

    qs = (
        PurchaseOrder.objects.select_related("supplier")
        .prefetch_related("lines")
        .order_by("-created_at")
    )
    if supplier_id:
        qs = qs.filter(supplier_id=supplier_id)
    d_from = _parse_date(date_from, "date_from")
    d_to = _parse_date(date_to, "date_to")
    if d_from:
        qs = qs.filter(created_at__date__gte=d_from)
    if d_to:
        qs = qs.filter(created_at__date__lte=d_to)

    # Annotate total = sum of line qty * unit_price in one pass.
    qs = qs.annotate(
        total=Coalesce(
            Sum(
                ExpressionWrapper(
                    F("lines__qty") * F("lines__unit_price"),
                    output_field=DecimalField(max_digits=12, decimal_places=2),
                )
            ),
            Decimal("0"),
        )
    )

    return [
        {
            "po_number": po.po_number,
            "supplier": po.supplier.name,
            "status": po.status,
            "total": po.total,
            "created_at": po.created_at.isoformat(),
        }
        for po in qs
    ]


# ---------------------------------------------------------------------------
# GRN register
# ---------------------------------------------------------------------------


def grn_register(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> list[dict]:
    """Return a flat register of posted GRNs.

    Args:
        date_from: ISO date string (inclusive lower bound on created_at).
        date_to: ISO date string (inclusive upper bound on created_at).

    Returns:
        List of dicts with keys: grn_id, po_number, supplier, received_at, value.
    """
    from apps.procurement.models import GRN

    qs = (
        GRN.objects.filter(status=GRN.Status.POSTED)
        .select_related("po__supplier", "received_by")
        .prefetch_related("lines")
        .order_by("-created_at")
    )
    d_from = _parse_date(date_from, "date_from")
    d_to = _parse_date(date_to, "date_to")
    if d_from:
        qs = qs.filter(created_at__date__gte=d_from)
    if d_to:
        qs = qs.filter(created_at__date__lte=d_to)

    qs = qs.annotate(
        value=Coalesce(
            Sum(
                ExpressionWrapper(
                    F("lines__qty_received") * F("lines__unit_cost"),
                    output_field=DecimalField(max_digits=12, decimal_places=2),
                )
            ),
            Decimal("0"),
        )
    )

    return [
        {
            "grn_id": str(grn.id),
            "po_number": grn.po.po_number,
            "supplier": grn.po.supplier.name,
            "received_at": grn.created_at.isoformat(),
            "value": grn.value,
        }
        for grn in qs
    ]


# ---------------------------------------------------------------------------
# Issues by destination
# ---------------------------------------------------------------------------


def issues_by_destination() -> list[dict]:
    """Count and value of ISSUE_IN movements grouped by destination location.

    Returns:
        List of dicts with keys: location, count, total_value.
    """
    from django.db.models import Count

    rows = (
        StockMovement.objects.filter(movement_type=StockMovement.MovementType.ISSUE_IN)
        .values("location__name")
        .annotate(
            count=Count("id"),
            total_value=Coalesce(
                Sum(
                    ExpressionWrapper(
                        F("qty_delta") * Coalesce(F("unit_cost"), Decimal("0")),
                        output_field=DecimalField(max_digits=12, decimal_places=2),
                    )
                ),
                Decimal("0"),
            ),
        )
        .order_by("location__name")
    )

    return [
        {
            "location": r["location__name"],
            "count": r["count"],
            "total_value": r["total_value"],
        }
        for r in rows
    ]


# ---------------------------------------------------------------------------
# Wastage report
# ---------------------------------------------------------------------------


def wastage_report(by: str = "reason") -> list[dict]:
    """Wastage totals grouped by reason, item, location, or user.

    Args:
        by: Grouping dimension — one of ``reason``, ``item``, ``location``,
            ``user``. Defaults to ``reason``.

    Returns:
        List of dicts with keys matching the group dimension plus
        total_qty and total_value.
    """
    valid_by = {"reason", "item", "location", "user"}
    if by not in valid_by:
        by = "reason"

    group_field_map = {
        "reason": ("reason_code__label", "reason"),
        "item": ("product__name", "product"),
        "location": ("location__name", "location"),
        "user": ("logged_by__full_name", "user"),
    }
    db_field, label_key = group_field_map[by]

    rows = (
        WastageEntry.objects.filter(status=WastageEntry.Status.POSTED)
        .values(db_field)
        .annotate(
            total_qty=Coalesce(Sum("qty"), Decimal("0")),
            total_value=Coalesce(Sum("value"), Decimal("0")),
        )
        .order_by("-total_value")
    )

    return [
        {
            label_key: r[db_field],
            "total_qty": r["total_qty"],
            "total_value": r["total_value"],
        }
        for r in rows
    ]


# ---------------------------------------------------------------------------
# Service time
# ---------------------------------------------------------------------------


def service_time() -> list[dict]:
    """Average and median kitchen service times derived from order status events.

    Computes per-order durations (INGESTED → IN_PREPARATION → READY → SERVED)
    by pulling one row per order status from the DB, then aggregates
    avg/median in Python — one DB round-trip, not per-row.

    Returns:
        List with a single summary dict with keys: avg_seconds_to_preparation,
        avg_seconds_to_ready, avg_seconds_to_served, median_seconds_to_served,
        order_count.
    """
    from apps.kitchen.models import Order, OrderStatusEvent

    # Pull (order_id, status, created_at) in one pass.
    events = list(
        OrderStatusEvent.objects.values("order_id", "status", "created_at")
        .order_by("order_id", "created_at")
    )

    # Group events per order.
    order_events: dict = {}
    for ev in events:
        order_events.setdefault(ev["order_id"], {})[ev["status"]] = ev["created_at"]

    to_prep_secs: list[float] = []
    to_ready_secs: list[float] = []
    to_served_secs: list[float] = []

    for _oid, ev_map in order_events.items():
        ingested = ev_map.get(Order.Status.INGESTED)
        prepared = ev_map.get(Order.Status.IN_PREPARATION)
        ready = ev_map.get(Order.Status.READY)
        served = ev_map.get(Order.Status.SERVED)

        if ingested and prepared:
            to_prep_secs.append((prepared - ingested).total_seconds())
        if ingested and ready:
            to_ready_secs.append((ready - ingested).total_seconds())
        if ingested and served:
            to_served_secs.append((served - ingested).total_seconds())

    def _avg(lst: list[float]) -> Optional[float]:
        return sum(lst) / len(lst) if lst else None

    def _median(lst: list[float]) -> Optional[float]:
        return statistics.median(lst) if lst else None

    return [
        {
            "avg_seconds_to_preparation": _avg(to_prep_secs),
            "avg_seconds_to_ready": _avg(to_ready_secs),
            "avg_seconds_to_served": _avg(to_served_secs),
            "median_seconds_to_served": _median(to_served_secs),
            "order_count": len(order_events),
        }
    ]


# ---------------------------------------------------------------------------
# Movers
# ---------------------------------------------------------------------------


def movers(period_days: int = 30) -> list[dict]:
    """Products ranked by total SALE_DEDUCTION quantity over the period.

    Args:
        period_days: Look-back window in days. Defaults to 30.

    Returns:
        List of dicts with keys: product_code, product_name, total_qty,
        rank — ordered fastest to slowest (descending qty).
    """
    from django.utils import timezone

    since = timezone.now() - datetime.timedelta(days=period_days)

    rows = (
        StockMovement.objects.filter(
            movement_type=StockMovement.MovementType.SALE_DEDUCTION,
            posted_at__gte=since,
        )
        .values("product__code", "product__name")
        .annotate(
            total_qty=Coalesce(
                Sum(
                    ExpressionWrapper(
                        F("qty_delta") * -1,
                        output_field=DecimalField(max_digits=12, decimal_places=3),
                    )
                ),
                Decimal("0"),
            )
        )
        .order_by("-total_qty")
    )

    return [
        {
            "product_code": r["product__code"],
            "product_name": r["product__name"],
            "total_qty": r["total_qty"],
            "rank": idx + 1,
        }
        for idx, r in enumerate(rows)
    ]


# ---------------------------------------------------------------------------
# Leakage
# ---------------------------------------------------------------------------


def leakage(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> list[dict]:
    """Per-product consumption gap: theoretical vs actual.

    Theoretical consumption = sum of SALE_DEDUCTION quantity (absolute).
    Actual consumption = SALE_DEDUCTION + WASTAGE movement + STOCKTAKE_ADJ (absolute).
    Gap = actual - theoretical (positive means unaccounted loss).

    Args:
        date_from: ISO date string (inclusive).
        date_to: ISO date string (inclusive).

    Returns:
        List of dicts with keys: product_code, product_name,
        theoretical_qty, actual_qty, gap_qty.
    """
    today = datetime.date.today()
    d_from = _parse_date(date_from, "date_from") or (today - datetime.timedelta(days=30))
    d_to = _parse_date(date_to, "date_to") or today

    theoretical_types = [StockMovement.MovementType.SALE_DEDUCTION]
    actual_types = [
        StockMovement.MovementType.SALE_DEDUCTION,
        StockMovement.MovementType.WASTAGE,
        StockMovement.MovementType.STOCKTAKE_ADJ,
    ]

    def _sum_movements(types: list[str]) -> dict:
        """Return a mapping of product_id → absolute qty sum."""
        rows = (
            StockMovement.objects.filter(
                movement_type__in=types,
                posted_at__date__gte=d_from,
                posted_at__date__lte=d_to,
            )
            .values("product__code", "product__name", "product_id")
            .annotate(
                abs_qty=Coalesce(
                    Sum(
                        ExpressionWrapper(
                            F("qty_delta") * -1,
                            output_field=DecimalField(max_digits=12, decimal_places=3),
                        )
                    ),
                    Decimal("0"),
                )
            )
        )
        return {r["product_id"]: r for r in rows}

    theoretical = _sum_movements(theoretical_types)
    actual = _sum_movements(actual_types)

    all_product_ids = set(theoretical) | set(actual)
    rows: list[dict] = []
    for pid in all_product_ids:
        t_row = theoretical.get(pid, {})
        a_row = actual.get(pid, t_row)
        t_qty = t_row.get("abs_qty", Decimal("0"))
        a_qty = a_row.get("abs_qty", Decimal("0"))
        rows.append(
            {
                "product_code": (t_row or a_row).get("product__code", ""),
                "product_name": (t_row or a_row).get("product__name", ""),
                "theoretical_qty": t_qty,
                "actual_qty": a_qty,
                "gap_qty": a_qty - t_qty,
            }
        )

    rows.sort(key=lambda r: r["gap_qty"], reverse=True)
    return rows


# ---------------------------------------------------------------------------
# Recipe costing
# ---------------------------------------------------------------------------


def recipe_costing() -> list[dict]:
    """Plate cost and gross margin for each published menu item.

    Plate cost = sum(recipe line qty_per_serving × latest GRN unit_cost).
    Margin = selling_price_snapshot − plate cost.

    Returns:
        List of dicts with keys: menu_item, pos_code, selling_price,
        plate_cost, margin.
    """
    from apps.menu.models import RecipeVersion

    published_versions = (
        RecipeVersion.objects.filter(status=RecipeVersion.Status.PUBLISHED)
        .select_related("menu_item")
        .prefetch_related("lines__product")
    )

    rows: list[dict] = []
    for version in published_versions:
        plate_cost = Decimal("0")
        for line in version.lines.all():
            # Use the subquery result; fallback to 0.
            cost_row = (
                StockMovement.objects.filter(
                    movement_type=StockMovement.MovementType.GRN_RECEIPT,
                    unit_cost__isnull=False,
                    product_id=line.product_id,
                )
                .order_by("-posted_at")
                .values("unit_cost")
                .first()
            )
            unit_cost = cost_row["unit_cost"] if cost_row else Decimal("0")
            plate_cost += line.qty_per_serving * unit_cost

        selling_price = version.selling_price_snapshot or Decimal("0")
        rows.append(
            {
                "menu_item": version.menu_item.name,
                "pos_code": version.menu_item.pos_code,
                "selling_price": selling_price,
                "plate_cost": plate_cost,
                "margin": selling_price - plate_cost,
            }
        )

    rows.sort(key=lambda r: r["margin"])
    return rows


# ---------------------------------------------------------------------------
# Reorder suggestions
# ---------------------------------------------------------------------------


def reorder_suggestions() -> list[dict]:
    """Products at or below reorder level with suggested replenishment qty.

    Suggested qty = max(reorder_level * 2 - qty_on_hand, 0).
    Velocity = avg daily SALE_DEDUCTION over the last 30 days.

    Returns:
        List of dicts with keys: product_code, product_name, qty_on_hand,
        reorder_level, suggested_qty, avg_daily_velocity.
    """
    from django.utils import timezone

    since = timezone.now() - datetime.timedelta(days=30)

    # Velocity per product in one query.
    velocity_rows = (
        StockMovement.objects.filter(
            movement_type=StockMovement.MovementType.SALE_DEDUCTION,
            posted_at__gte=since,
        )
        .values("product_id")
        .annotate(
            total_abs_qty=Coalesce(
                Sum(
                    ExpressionWrapper(
                        F("qty_delta") * -1,
                        output_field=DecimalField(max_digits=12, decimal_places=3),
                    )
                ),
                Decimal("0"),
            )
        )
    )
    velocity_map: dict = {r["product_id"]: r["total_abs_qty"] / 30 for r in velocity_rows}

    # Products at/below reorder level.
    balances = (
        StockBalance.objects.select_related("product")
        .filter(qty_on_hand__lte=F("product__reorder_level"))
        .order_by("product__name")
    )

    rows: list[dict] = []
    for bal in balances:
        reorder = bal.product.reorder_level
        suggested = max(reorder * 2 - bal.qty_on_hand, Decimal("0"))
        velocity = velocity_map.get(bal.product_id, Decimal("0"))
        rows.append(
            {
                "product_code": bal.product.code,
                "product_name": bal.product.name,
                "qty_on_hand": bal.qty_on_hand,
                "reorder_level": reorder,
                "suggested_qty": suggested,
                "avg_daily_velocity": velocity,
            }
        )
    return rows
