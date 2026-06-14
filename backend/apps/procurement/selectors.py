"""Procurement read selectors: reporting and history queries."""

import datetime
from typing import Any

from django.db.models import QuerySet

from apps.masterdata.models import Supplier
from apps.procurement.models import GRN, InvoiceMatch, PurchaseBudget, PurchaseOrder, SupplierInvoice


def budget_vs_actual(
    date_from: datetime.date,
    date_to: datetime.date,
) -> list[dict]:
    """Return a list comparing budget estimates to GRN actuals for a date range.

    Each entry contains the budget id, status, total_estimated, and the sum of
    all received GRN line values posted within the date range.

    Args:
        date_from: Start date (inclusive) for filtering budgets by creation date.
        date_to: End date (inclusive) for filtering budgets.

    Returns:
        A list of dicts with keys: budget_id, status, total_estimated, actual_cost.
    """
    budgets: QuerySet[PurchaseBudget] = PurchaseBudget.objects.filter(
        created_at__date__gte=date_from,
        created_at__date__lte=date_to,
    ).prefetch_related("purchase_orders__grns__lines")

    result: list[dict] = []
    for budget in budgets:
        actual_cost = sum(
            grn_line.qty_received * grn_line.unit_cost
            for po in budget.purchase_orders.all()
            for grn in po.grns.filter(status=GRN.Status.POSTED)
            for grn_line in grn.lines.all()
        )
        result.append(
            {
                "budget_id": str(budget.id),
                "status": budget.status,
                "total_estimated": budget.total_estimated,
                "actual_cost": actual_cost,
            }
        )
    return result


def supplier_history(supplier: Supplier) -> dict[str, Any]:
    """Return a history summary for a given supplier.

    Args:
        supplier: The Supplier to query.

    Returns:
        A dict with keys: supplier_id, pos, grns, invoices — each a QuerySet.
    """
    pos: QuerySet[PurchaseOrder] = PurchaseOrder.objects.filter(
        supplier=supplier
    ).select_related("budget", "supplier").prefetch_related("lines")

    po_ids = pos.values_list("id", flat=True)

    grns: QuerySet[GRN] = GRN.objects.filter(po_id__in=po_ids).select_related(
        "po", "received_by"
    ).prefetch_related("lines")

    invoices: QuerySet[SupplierInvoice] = SupplierInvoice.objects.filter(
        supplier=supplier
    ).select_related("po")

    return {
        "supplier_id": str(supplier.id),
        "pos": pos,
        "grns": grns,
        "invoices": invoices,
    }
