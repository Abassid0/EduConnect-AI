import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.flows import FlowResult
from app.models.conversation import Conversation
from app.utils.whatsapp_helpers import build_text_payload

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
        try:
            from app.services import payment_plan_service, registration_service
            parent = await registration_service.get_parent_by_whatsapp(to, db)
            if not parent:
                return FlowResult(
                    flow_complete=True,
                    flow_data={},
                    reply=build_text_payload(to, "No account found. Reply 'menu' to continue."),
                )

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

    return FlowResult(flow_complete=True, flow_data={})
