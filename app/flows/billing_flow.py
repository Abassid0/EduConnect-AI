import logging
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.flows import FlowResult
from app.models.conversation import Conversation
from app.services import billing_service, registration_service
from app.utils.whatsapp_helpers import (
    build_interactive_button_payload,
    build_text_payload,
)

logger = logging.getLogger(__name__)


async def handle_step(
    step: str,
    user_input: str,
    flow_data: dict[str, Any],
    conversation: Conversation,
    db: AsyncSession,
) -> FlowResult:
    to = conversation.whatsapp_id

    if step == "start":
        parent = await registration_service.get_parent_by_whatsapp(to, db)
        if not parent:
            return FlowResult(
                flow_complete=True,
                flow_data={},
                reply=build_text_payload(
                    to,
                    "You don't have an account yet. "
                    "Register a student first!\n\n"
                    "Reply 'menu' to get started.",
                ),
            )

        flow_data["parent_id"] = str(parent.id)
        balance = await billing_service.get_parent_balance(parent.id, db)

        total_invoiced = balance["total_invoiced"]
        total_paid = balance["total_paid"]
        outstanding = balance["outstanding"]
        invoice_count = balance["invoice_count"]
        overdue_count = balance["overdue_count"]

        if invoice_count == 0 and outstanding == 0:
            return FlowResult(
                flow_complete=True,
                flow_data={},
                reply=build_text_payload(
                    to,
                    "You have no invoices or outstanding fees.\n"
                    "Everything is up to date!\n\n"
                    "Reply 'menu' to see options.",
                ),
            )

        overdue_line = ""
        if overdue_count > 0:
            overdue_line = f"\n*Overdue:* {overdue_count} invoice(s)"

        body = (
            f"*Your Account Balance*\n\n"
            f"Total Invoiced: N{total_invoiced:,.0f}\n"
            f"Total Paid: N{total_paid:,.0f}\n"
            f"Outstanding: N{outstanding:,.0f}\n"
            f"Invoices: {invoice_count}"
            f"{overdue_line}\n"
        )

        try:
            from app.services import payment_plan_service as _pps
            active_plan = await _pps.get_active_plan_for_parent(parent.id, db)
        except Exception:
            active_plan = None

        if outstanding > 0:
            if active_plan:
                buttons = [
                    {"id": "bal_plan", "title": "View Plan"},
                    {"id": "bal_details", "title": "View Details"},
                    {"id": "bal_menu", "title": "Main Menu"},
                ]
            else:
                buttons = [
                    {"id": "bal_pay", "title": "Make Payment"},
                    {"id": "bal_details", "title": "View Details"},
                    {"id": "bal_menu", "title": "Main Menu"},
                ]
        else:
            buttons = [
                {"id": "bal_details", "title": "View Details"},
                {"id": "bal_menu", "title": "Main Menu"},
            ]

        return FlowResult(
            next_step="after_balance",
            flow_data=flow_data,
            reply=build_interactive_button_payload(
                to,
                body=body,
                buttons=buttons,
                header="Balance Summary",
            ),
        )

    if step == "after_balance":
        choice = user_input.strip().lower()

        if choice == "bal_pay":
            return FlowResult(
                next_flow="payment",
                next_step="start",
                flow_data={},
            )

        if choice == "bal_plan":
            return FlowResult(
                next_flow="payment_plan",
                next_step="start",
                flow_data={},
            )

        if choice == "bal_details":
            return await _show_invoice_details(flow_data, to, db)

        return FlowResult(
            next_flow="main_menu",
            next_step="show",
            flow_data={},
        )

    if step == "after_details":
        choice = user_input.strip().lower()
        if choice == "det_pay":
            return FlowResult(
                next_flow="payment",
                next_step="start",
                flow_data={},
            )
        if choice == "det_find":
            return _ask_for_invoice_number(flow_data, to)
        return FlowResult(
            next_flow="main_menu",
            next_step="show",
            flow_data={},
        )

    if step == "awaiting_invoice_number":
        return await _lookup_invoice(user_input, flow_data, to, db)

    if step == "after_invoice_view":
        choice = user_input.strip().lower()
        if choice == "inv_pay":
            return FlowResult(
                next_flow="payment",
                next_step="start",
                flow_data={},
            )
        if choice == "inv_another":
            return _ask_for_invoice_number(flow_data, to)
        return FlowResult(
            next_flow="main_menu",
            next_step="show",
            flow_data={},
        )

    return FlowResult(
        flow_complete=True,
        flow_data={},
        reply=build_text_payload(
            to, "Something went wrong. Reply 'menu' to start over."
        ),
    )


async def _show_invoice_details(
    flow_data: dict[str, Any],
    to: str,
    db: AsyncSession,
) -> FlowResult:
    parent_id_str = flow_data.get("parent_id")
    if not parent_id_str:
        return FlowResult(flow_complete=True, flow_data={})

    import uuid
    parent_id = uuid.UUID(parent_id_str)
    invoices = await billing_service.get_outstanding_invoices(parent_id, db)

    if not invoices:
        return FlowResult(
            flow_complete=True,
            flow_data={},
            reply=build_text_payload(
                to,
                "No outstanding invoices found.\n\n"
                "Reply 'menu' to see options.",
            ),
        )

    lines = ["*Outstanding Invoices*\n"]
    for inv in invoices[:5]:
        remaining = inv.total_amount - inv.amount_paid
        status_emoji = "⚠️" if inv.status == "overdue" else "📋"
        due = f" (due {inv.due_date.strftime('%d/%m/%Y')})" if inv.due_date else ""
        lines.append(f"{status_emoji} *{inv.invoice_number}*{due}")
        lines.append(f"  {inv.title}")
        if hasattr(inv, "items") and inv.items:
            for item in inv.items:
                lines.append(f"    - {item.description}: N{item.total_amount:,.0f}")
        lines.append(f"  *Total:* N{inv.total_amount:,.0f}")
        if inv.amount_paid > 0:
            lines.append(f"  Paid: N{inv.amount_paid:,.0f} | Remaining: N{remaining:,.0f}")
        lines.append("")

    total_outstanding = sum(
        inv.total_amount - inv.amount_paid for inv in invoices
    )
    lines.append(f"*Total Outstanding: N{total_outstanding:,.0f}*")

    buttons = [
        {"id": "det_pay", "title": "Make Payment"},
        {"id": "det_find", "title": "Find Invoice"},
        {"id": "det_menu", "title": "Main Menu"},
    ]

    return FlowResult(
        next_step="after_details",
        flow_data=flow_data,
        reply=build_interactive_button_payload(
            to,
            body="\n".join(lines),
            buttons=buttons,
            header="Invoice Details",
        ),
    )


def _ask_for_invoice_number(
    flow_data: dict[str, Any],
    to: str,
) -> FlowResult:
    return FlowResult(
        next_step="awaiting_invoice_number",
        flow_data=flow_data,
        reply=build_text_payload(
            to,
            "*Find an Invoice*\n\n"
            "Please type the invoice number you want to view.\n\n"
            "For example: INV-20260901-12345\n\n"
            "Reply 'menu' to go back.",
        ),
    )


async def _lookup_invoice(
    user_input: str,
    flow_data: dict[str, Any],
    to: str,
    db: AsyncSession,
) -> FlowResult:
    parent_id_str = flow_data.get("parent_id")
    if not parent_id_str:
        return FlowResult(
            flow_complete=True,
            flow_data={},
            reply=build_text_payload(
                to, "Something went wrong. Reply 'menu' to start over."
            ),
        )

    import uuid
    parent_id = uuid.UUID(parent_id_str)
    typed = user_input.strip()

    if typed.lower() in ("menu", "back", "cancel"):
        return FlowResult(
            next_flow="main_menu",
            next_step="show",
            flow_data={},
        )

    if billing_service.normalise_invoice_number(typed) is None:
        return FlowResult(
            next_step="awaiting_invoice_number",
            flow_data=flow_data,
            reply=build_text_payload(
                to,
                f"'{typed}' doesn't look like an invoice number.\n\n"
                "Invoice numbers look like INV-20260901-12345.\n"
                "Please check the number and type it again, "
                "or reply 'menu' to go back.",
            ),
        )

    invoice = await billing_service.get_invoice_by_number_for_parent(
        typed, parent_id, db
    )

    if not invoice:
        return FlowResult(
            next_step="awaiting_invoice_number",
            flow_data=flow_data,
            reply=build_text_payload(
                to,
                "We couldn't find that invoice on your account.\n\n"
                "Please check the number and type it again, "
                "or reply 'menu' to go back.",
            ),
        )

    return _render_invoice(invoice, flow_data, to)


def _render_invoice(
    invoice: Any,
    flow_data: dict[str, Any],
    to: str,
) -> FlowResult:
    remaining = invoice.total_amount - invoice.amount_paid

    status_labels = {
        "paid": "Paid",
        "partial": "Partly paid",
        "overdue": "Overdue",
        "unpaid": "Unpaid",
        "cancelled": "Cancelled",
    }
    status_label = status_labels.get(invoice.status, invoice.status.title())

    lines = [
        f"*{invoice.invoice_number}*",
        invoice.title,
        "",
    ]

    if invoice.academic_term:
        lines.append(f"Term: {invoice.academic_term}")
    if invoice.due_date:
        lines.append(f"Due: {invoice.due_date.strftime('%d/%m/%Y')}")
    lines.append(f"Status: {status_label}")
    lines.append("")

    if invoice.items:
        lines.append("*Breakdown*")
        for item in invoice.items:
            if item.quantity and item.quantity > 1:
                lines.append(
                    f"  {item.description} x{item.quantity}: "
                    f"N{item.total_amount:,.0f}"
                )
            else:
                lines.append(f"  {item.description}: N{item.total_amount:,.0f}")
        lines.append("")

    lines.append(f"*Total:* N{invoice.total_amount:,.0f}")
    if invoice.amount_paid > 0:
        lines.append(f"Paid: N{invoice.amount_paid:,.0f}")
    if remaining > 0:
        lines.append(f"*Remaining:* N{remaining:,.0f}")

    if invoice.notes:
        lines.append("")
        lines.append(invoice.notes)

    buttons = []
    if invoice.status not in ("paid", "cancelled") and remaining > 0:
        buttons.append({"id": "inv_pay", "title": "Make Payment"})
    buttons.append({"id": "inv_another", "title": "Find Another"})
    buttons.append({"id": "inv_menu", "title": "Main Menu"})

    return FlowResult(
        next_step="after_invoice_view",
        flow_data=flow_data,
        reply=build_interactive_button_payload(
            to,
            body="\n".join(lines),
            buttons=buttons,
            header="Invoice",
        ),
    )
