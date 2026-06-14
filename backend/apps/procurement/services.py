"""Procurement write services: budget submission, PO creation, GRN posting, invoice matching."""

from decimal import Decimal
from typing import Any, Optional

from django.core.files.base import ContentFile
from django.db import transaction

from apps.core.exceptions import DomainError
from apps.core.models import Approval
from apps.core.services import log_audit, submit_for_approval
from apps.inventory.models import StockMovement
from apps.inventory.services import MovementLine, post_movements
from apps.masterdata.models import Location, Supplier
from apps.notifications.models import Notification
from apps.notifications.services import notify_role
from apps.procurement.models import (
    GRN,
    BudgetLine,
    GRNLine,
    InvoiceMatch,
    POLine,
    POSendLog,
    PurchaseBudget,
    PurchaseOrder,
    SupplierInvoice,
)
from apps.users.models import User


@transaction.atomic
def submit_budget(budget: PurchaseBudget, user: User) -> Approval:
    """Submit a DRAFT budget for manager approval and notify managers.

    Args:
        budget: The PurchaseBudget instance to submit (must be DRAFT).
        user: The user performing the submission.

    Returns:
        The newly created Approval record.

    Raises:
        DomainError: If the budget is not in DRAFT status.
    """
    if budget.status != PurchaseBudget.Status.DRAFT:
        raise DomainError("Only DRAFT budgets can be submitted for approval.")

    budget.status = PurchaseBudget.Status.SUBMITTED
    budget.save(update_fields=["status", "updated_at"])

    approval = submit_for_approval(subject=budget, scope="", requested_by=user, value=None)

    notify_role(
        role=User.Role.MANAGER,
        kind=Notification.Kind.APPROVAL_PENDING,
        body=f"Purchase budget {budget.id} has been submitted and requires your approval.",
        subject=budget,
    )

    return approval


@transaction.atomic
def create_po(
    budget: PurchaseBudget,
    supplier: Supplier,
    lines: list[dict],
    user: User,
) -> PurchaseOrder:
    """Create a PurchaseOrder against an approved budget.

    Args:
        budget: The PurchaseBudget (must be APPROVED).
        supplier: The Supplier to raise the PO against.
        lines: List of dicts with keys: product_id, qty, unit_price.
        user: The user creating the PO.

    Returns:
        The newly created PurchaseOrder with its lines.

    Raises:
        DomainError: If the budget is not APPROVED.
    """
    if budget.status != PurchaseBudget.Status.APPROVED:
        raise DomainError("Purchase orders can only be created against APPROVED budgets.")

    count = PurchaseOrder.objects.count()
    po_number = f"PO-{count + 1:06d}"

    po = PurchaseOrder.objects.create(
        budget=budget,
        supplier=supplier,
        po_number=po_number,
    )

    POLine.objects.bulk_create(
        [
            POLine(
                po=po,
                product_id=line["product_id"],
                qty=line["qty"],
                unit_price=line["unit_price"],
            )
            for line in lines
        ]
    )

    return po


@transaction.atomic
def send_po(po: PurchaseOrder, user: User) -> POSendLog:
    """Attempt to send a PurchaseOrder PDF to the supplier via email.

    Generates a PDF using weasyprint if available. If the supplier has an email
    address the PDF is attached and emailed; otherwise the PO is flagged for
    manual contact.

    Args:
        po: The PurchaseOrder to send.
        user: The user performing the send action.

    Returns:
        The POSendLog record for this send attempt.
    """
    from django.core.mail import EmailMessage

    pdf_bytes: Optional[bytes] = None

    try:
        import weasyprint  # type: ignore[import]

        html_content = _build_po_html(po)
        pdf_bytes = weasyprint.HTML(string=html_content).write_pdf()
    except ImportError:
        pass
    except Exception:
        pass

    supplier = po.supplier

    if supplier.email:
        msg = EmailMessage(
            subject=f"Purchase Order {po.po_number}",
            body=(
                f"Dear {supplier.contact_name or supplier.name},\n\n"
                f"Please find attached Purchase Order {po.po_number}.\n\n"
                "Regards,\nFlying Foods Procurement"
            ),
            to=[supplier.email],
        )
        if pdf_bytes:
            msg.attach(f"{po.po_number}.pdf", pdf_bytes, "application/pdf")
            po.pdf_file.save(f"{po.po_number}.pdf", ContentFile(pdf_bytes), save=False)

        msg.send(fail_silently=True)

        po.status = PurchaseOrder.Status.SENT
        po.save(update_fields=["status", "pdf_file", "updated_at"])

        send_log = POSendLog.objects.create(
            po=po,
            recipient=supplier.email,
            result=POSendLog.Result.SENT,
        )
    else:
        po.status = PurchaseOrder.Status.MANUAL_CONTACT_REQUIRED
        po.save(update_fields=["status", "updated_at"])

        send_log = POSendLog.objects.create(
            po=po,
            recipient=supplier.name,
            result=POSendLog.Result.NONE_NO_EMAIL,
        )

    log_audit(
        entity="PurchaseOrder",
        entity_id=str(po.pk),
        action="send",
        user=user,
        before={},
        after={"status": po.status},
    )

    return send_log


def _build_po_html(po: PurchaseOrder) -> str:
    """Render a minimal HTML representation of a PurchaseOrder for PDF generation.

    Args:
        po: The PurchaseOrder to render.

    Returns:
        An HTML string suitable for weasyprint.
    """
    lines_html = "".join(
        f"<tr><td>{line.product_id}</td><td>{line.qty}</td><td>{line.unit_price}</td></tr>"
        for line in po.lines.select_related("product").all()
    )
    return f"""
    <html>
    <body>
      <h1>Purchase Order {po.po_number}</h1>
      <p>Supplier: {po.supplier.name}</p>
      <table>
        <thead><tr><th>Product</th><th>Qty</th><th>Unit Price</th></tr></thead>
        <tbody>{lines_html}</tbody>
      </table>
    </body>
    </html>
    """


@transaction.atomic
def post_grn(
    po: PurchaseOrder,
    lines_data: list[dict],
    received_by: User,
) -> GRN:
    """Create and post a Goods Received Note against a PurchaseOrder.

    Updates fulfilled quantities on PO lines, posts GRN_RECEIPT stock movements,
    and updates the PO status to PARTIALLY_RECEIVED or RECEIVED.

    Args:
        po: The PurchaseOrder being received against.
        lines_data: List of dicts with keys: po_line_id, qty_received, unit_cost,
                    condition (optional), variance_reason_id (optional).
        received_by: The user receiving the goods.

    Returns:
        The posted GRN.
    """
    grn = GRN.objects.create(po=po, received_by=received_by, status=GRN.Status.DRAFT)

    grn_lines: list[GRNLine] = []
    for item in lines_data:
        grn_lines.append(
            GRNLine(
                grn=grn,
                po_line_id=item["po_line_id"],
                qty_received=item["qty_received"],
                unit_cost=item["unit_cost"],
                condition=item.get("condition", ""),
                variance_reason_id=item.get("variance_reason_id"),
            )
        )
    GRNLine.objects.bulk_create(grn_lines)

    stores_location = Location.objects.filter(kind=Location.Kind.STORES).first()

    movement_lines: list[MovementLine] = []
    for item in lines_data:
        if stores_location:
            po_line = POLine.objects.get(pk=item["po_line_id"])
            movement_lines.append(
                MovementLine(
                    product_id=po_line.product_id,
                    location_id=stores_location.pk,
                    qty_delta=Decimal(str(item["qty_received"])),
                    movement_type=StockMovement.MovementType.GRN_RECEIPT,
                    unit_cost=Decimal(str(item["unit_cost"])),
                )
            )

    if movement_lines:
        post_movements(
            document_type="GRN",
            document_id=grn.pk,
            lines=movement_lines,
            posted_by=received_by,
        )

    for item in lines_data:
        po_line = POLine.objects.select_for_update().get(pk=item["po_line_id"])
        po_line.fulfilled_qty = (po_line.fulfilled_qty or Decimal("0")) + Decimal(
            str(item["qty_received"])
        )
        po_line.save(update_fields=["fulfilled_qty", "updated_at"])

    all_lines = list(po.lines.all())
    all_fulfilled = all(line.fulfilled_qty >= line.qty for line in all_lines)
    po.status = (
        PurchaseOrder.Status.RECEIVED if all_fulfilled else PurchaseOrder.Status.PARTIALLY_RECEIVED
    )
    po.save(update_fields=["status", "updated_at"])

    grn.status = GRN.Status.POSTED
    grn.save(update_fields=["status", "updated_at"])

    return grn


@transaction.atomic
def match_invoice(
    po: PurchaseOrder,
    invoice_ref: str,
    amount: Decimal,
    user: User,
    file: Any = None,
) -> tuple[SupplierInvoice, InvoiceMatch]:
    """Create a SupplierInvoice and perform a 3-way match against the PO and GRNs.

    Compares the invoice amount to both the PO value and the total GRN received
    value. Flags discrepancies if either differs from the invoice amount.

    Args:
        po: The PurchaseOrder being invoiced.
        invoice_ref: The supplier's invoice reference number.
        amount: The invoice amount submitted by the supplier.
        user: The user recording the invoice.
        file: Optional uploaded invoice file.

    Returns:
        A (SupplierInvoice, InvoiceMatch) tuple.
    """
    invoice = SupplierInvoice.objects.create(
        supplier=po.supplier,
        po=po,
        invoice_ref=invoice_ref,
        amount=amount,
        file=file,
    )

    po_value: Decimal = sum(
        (line.qty * line.unit_price for line in po.lines.all()),
        Decimal("0"),
    )

    grn_value: Decimal = sum(
        (
            grn_line.qty_received * grn_line.unit_cost
            for grn in po.grns.filter(status=GRN.Status.POSTED)
            for grn_line in grn.lines.all()
        ),
        Decimal("0"),
    )

    discrepancies: dict = {}
    if amount != po_value:
        discrepancies["po_value"] = {
            "expected": str(po_value),
            "actual": str(amount),
        }
    if amount != grn_value:
        discrepancies["grn_value"] = {
            "expected": str(grn_value),
            "actual": str(amount),
        }

    match_status = (
        InvoiceMatch.Status.MATCHED if not discrepancies else InvoiceMatch.Status.DISCREPANCY
    )

    match = InvoiceMatch.objects.create(
        po=po,
        invoice=invoice,
        status=match_status,
        discrepancies=discrepancies,
    )

    return invoice, match


@transaction.atomic
def resolve_match(match: InvoiceMatch, user: User) -> InvoiceMatch:
    """Mark a disputed or discrepancy invoice match as resolved.

    Args:
        match: The InvoiceMatch to resolve.
        user: The user resolving the match.

    Returns:
        The updated InvoiceMatch.
    """
    match.status = InvoiceMatch.Status.RESOLVED
    match.save(update_fields=["status", "updated_at"])
    log_audit(
        entity="InvoiceMatch",
        entity_id=str(match.pk),
        action="resolve",
        user=user,
        after={"status": match.status},
    )
    return match


@transaction.atomic
def dispute_match(match: InvoiceMatch, user: User) -> InvoiceMatch:
    """Flag a discrepancy invoice match as disputed.

    Args:
        match: The InvoiceMatch to dispute.
        user: The user raising the dispute.

    Returns:
        The updated InvoiceMatch.
    """
    match.status = InvoiceMatch.Status.DISPUTED
    match.save(update_fields=["status", "updated_at"])
    log_audit(
        entity="InvoiceMatch",
        entity_id=str(match.pk),
        action="dispute",
        user=user,
        after={"status": match.status},
    )
    return match


@transaction.atomic
def escalate_match(match: InvoiceMatch, user: User) -> InvoiceMatch:
    """Escalate a disputed invoice match for senior review.

    Args:
        match: The InvoiceMatch to escalate.
        user: The user escalating the match.

    Returns:
        The updated InvoiceMatch.
    """
    match.status = InvoiceMatch.Status.ESCALATED
    match.save(update_fields=["status", "updated_at"])
    log_audit(
        entity="InvoiceMatch",
        entity_id=str(match.pk),
        action="escalate",
        user=user,
        after={"status": match.status},
    )
    return match
