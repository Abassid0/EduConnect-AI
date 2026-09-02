import logging
import uuid
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.flows import FlowResult
from app.models.conversation import Conversation
from app.utils.whatsapp_helpers import (
    build_interactive_button_payload,
    build_text_payload,
)

logger = logging.getLogger(__name__)


def _schedule_preview(total: Decimal, start: date) -> list[str]:
    """Dates and amounts the parent would owe under the school's split."""
    from app.services.payment_plan_service import _add_frequency

    count = settings.INSTALLMENT_COUNT
    unit = (total / count).quantize(Decimal("0.01"))
    remainder = total - unit * (count - 1)

    lines = []
    due = start
    for i in range(1, count + 1):
        amount = remainder if i == count else unit
        lines.append(f"  {i}. N{amount:,.0f} — {due.strftime('%d %b %Y')}")
        if i < count:
            due = _add_frequency(due, settings.INSTALLMENT_FREQUENCY)
    return lines


async def _offer_plan(
    invoice_id: str, flow_data: dict[str, Any], to: str, db: AsyncSession
) -> FlowResult:
    """Show the instalment schedule for an invoice and ask to confirm."""
    from app.services import billing_service

    invoice = await billing_service.get_invoice(uuid.UUID(invoice_id), db)
    if not invoice:
        return FlowResult(
            flow_complete=True,
            flow_data={},
            reply=build_text_payload(
                to, "We could not find that invoice. Reply 'menu' to continue."
            ),
        )

    start = date.today() + timedelta(days=7)
    lines = [
        f"*Pay {invoice.invoice_number} in instalments*",
        "",
        f"Total: N{invoice.total_amount:,.0f}",
        f"Split into {settings.INSTALLMENT_COUNT} "
        f"{settings.INSTALLMENT_FREQUENCY} payments:",
        "",
    ]
    lines.extend(_schedule_preview(invoice.total_amount, start))
    lines.append("")
    lines.append("Shall we set this up?")

    flow_data["plan_start_date"] = start.isoformat()

    return FlowResult(
        next_step="confirm_plan",
        flow_data=flow_data,
        reply=build_interactive_button_payload(
            to,
            body="\n".join(lines),
            buttons=[
                {"id": "plan_yes", "title": "Yes, set it up"},
                {"id": "plan_no", "title": "Pay Full Instead"},
            ],
            header="Payment Plan",
        ),
    )


async def handle_step(
    step: str,
    user_input: str,
    flow_data: dict[str, Any],
    conversation: Conversation,
    db: AsyncSession,
) -> FlowResult:
    to = conversation.whatsapp_id

    if step == "start":
        try:
            from app.services import payment_plan_service, registration_service
            parent = await registration_service.get_parent_by_whatsapp(to, db)
            if not parent:
                return FlowResult(
                    flow_complete=True,
                    flow_data={},
                    reply=build_text_payload(to, "No account found. Reply 'menu' to continue."),
                )

            # Arriving from registration with a fresh invoice: offer the
            # school's instalment split rather than an existing-plan summary.
            invoice_id = flow_data.get("invoice_id")
            if invoice_id:
                return await _offer_plan(invoice_id, flow_data, to, db)

            summary = await payment_plan_service.get_parent_plan_summary(parent.id, db)
            if not summary:
                return FlowResult(
                    flow_complete=True,
                    flow_data={},
                    reply=build_text_payload(
                        to, "You don't have an active payment plan.\n\nReply 'menu' to see options."
                    ),
                )

            paid = summary["paid_amount"]
            total = summary["total_amount"]
            remaining = summary["remaining_amount"]
            paid_count = summary["paid_count"]
            count = summary["installment_count"]
            freq = summary["frequency"].capitalize()
            overdue_count = summary["overdue_count"]

            overdue_line = f"\n*Overdue: {overdue_count} installment(s)*" if overdue_count else ""

            next_line = ""
            if summary["next_installment"]:
                ni = summary["next_installment"]
                due_str = ni["due_date"].strftime("%d/%m/%Y")
                next_line = f"\nNext due: N{ni['amount']:,.0f} on {due_str}"
                if ni["status"] == "overdue":
                    next_line = f"\n*OVERDUE: N{ni['amount']:,.0f} (was due {due_str})*"

            body = (
                f"*Your Payment Plan*\n\n"
                f"Frequency: {freq}\n"
                f"Total: N{total:,.0f}\n"
                f"Paid: N{paid:,.0f} ({paid_count} of {count} installments)\n"
                f"Remaining: N{remaining:,.0f}"
                f"{next_line}"
                f"{overdue_line}\n\n"
                f"Reply 'menu' to return."
            )

            return FlowResult(
                flow_complete=True,
                flow_data={},
                reply=build_text_payload(to, body),
            )

        except Exception:
            logger.exception("Payment plan flow error for %s", to)
            return FlowResult(
                flow_complete=True,
                flow_data={},
                reply=build_text_payload(to, "Could not load your plan. Reply 'menu' to continue."),
            )

    if step == "confirm_plan":
        choice = user_input.strip().lower()

        if choice != "plan_yes":
            # "Pay Full Instead" — hand over to the normal payment flow.
            return FlowResult(
                next_flow="payment",
                next_step="start",
                flow_data={},
            )

        from app.services import payment_plan_service, registration_service

        parent = await registration_service.get_parent_by_whatsapp(to, db)
        invoice_id = flow_data.get("invoice_id")
        if not parent or not invoice_id:
            return FlowResult(
                flow_complete=True,
                flow_data={},
                reply=build_text_payload(
                    to, "Something went wrong. Reply 'menu' to start over."
                ),
            )

        start_raw = flow_data.get("plan_start_date")
        start = (
            date.fromisoformat(start_raw)
            if start_raw
            else date.today() + timedelta(days=7)
        )

        try:
            plan = await payment_plan_service.create_plan(
                invoice_id=uuid.UUID(invoice_id),
                parent_id=parent.id,
                installment_count=settings.INSTALLMENT_COUNT,
                frequency=settings.INSTALLMENT_FREQUENCY,
                start_date=start,
                db=db,
            )
        except ValueError as exc:
            return FlowResult(
                flow_complete=True,
                flow_data={},
                reply=build_text_payload(to, f"{exc}\n\nReply 'menu' to continue."),
            )
        except Exception:
            logger.exception("Failed to create payment plan for %s", to)
            return FlowResult(
                flow_complete=True,
                flow_data={},
                reply=build_text_payload(
                    to,
                    "We could not set up the plan just now. "
                    "Reply 'menu' and try again, or contact the school.",
                ),
            )

        first = min(plan.installments, key=lambda i: i.installment_number)
        return FlowResult(
            flow_complete=True,
            flow_data={},
            reply=build_text_payload(
                to,
                f"*Payment plan created*\n\n"
                f"{plan.installment_count} {plan.frequency} payments "
                f"totalling N{plan.total_amount:,.0f}.\n\n"
                f"First payment: N{first.amount:,.0f} due "
                f"{first.due_date.strftime('%d %b %Y')}.\n\n"
                f"We'll remind you before each one is due.\n"
                f"Reply 'menu' to continue.",
            ),
        )

    return FlowResult(flow_complete=True, flow_data={})
