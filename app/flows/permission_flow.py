import logging
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.flows import FlowResult
from app.models.conversation import Conversation
from app.services import permission_service
from app.utils.whatsapp_helpers import build_interactive_button_payload, build_text_payload

logger = logging.getLogger(__name__)


async def handle_step(
    step: str,
    user_input: str,
    flow_data: dict[str, Any],
    conversation: Conversation,
    db: AsyncSession,
) -> FlowResult:
    to = conversation.whatsapp_id
    slip_id_str = flow_data.get("slip_id", "")

    if step == "start":
        if not slip_id_str:
            return FlowResult(flow_complete=True, flow_data={})

        try:
            slip = await permission_service.get_slip(uuid.UUID(slip_id_str), db)
        except Exception:
            logger.exception("Error fetching permission slip %s", slip_id_str)
            return FlowResult(
                flow_complete=True,
                flow_data={},
                reply=build_text_payload(to, "Reply 'menu' to continue."),
            )

        if not slip or slip.status != "active":
            return FlowResult(flow_complete=True, flow_data={})

        date_line = ""
        if slip.event_date:
            date_line = f"\nEvent Date: {slip.event_date.strftime('%d/%m/%Y')}"

        deadline_line = ""
        if slip.deadline:
            deadline_line = f"\nRespond by: {slip.deadline.strftime('%d/%m/%Y')}"

        desc_line = f"\n\n{slip.description}" if slip.description else ""

        body = (
            f"*Consent Required: {slip.title}*"
            f"{desc_line}"
            f"{date_line}"
            f"{deadline_line}\n\n"
            f"Please confirm your response below."
        )

        buttons = [
            {"id": f"slip_yes_{slip_id_str}", "title": "Yes, I Consent"},
            {"id": f"slip_no_{slip_id_str}", "title": "No, I Decline"},
        ]

        return FlowResult(
            next_step="awaiting_response",
            flow_data=flow_data,
            reply=build_interactive_button_payload(
                to,
                body=body,
                buttons=buttons,
                header="Permission Slip",
                footer="Your response is recorded immediately.",
            ),
        )

    if step == "awaiting_response":
        choice = user_input.strip().lower()

        if choice.startswith("slip_yes_"):
            response = "yes"
        elif choice.startswith("slip_no_"):
            response = "no"
        else:
            return FlowResult(
                next_step="awaiting_response",
                flow_data=flow_data,
                reply=build_text_payload(to, "Please use the Yes or No buttons to respond."),
            )

        try:
            sid = uuid.UUID(slip_id_str)
            from app.models.parent import Parent
            from sqlalchemy import select
            parent_result = await db.execute(
                select(Parent).where(Parent.whatsapp_number == to)
            )
            parent = parent_result.scalar_one_or_none()
            parent_id = parent.id if parent else None

            if not parent_id:
                return FlowResult(
                    flow_complete=True,
                    flow_data={},
                    reply=build_text_payload(
                        to, "Could not find your account. Reply 'menu' to continue."
                    ),
                )

            await permission_service.record_response(
                slip_id=sid,
                parent_id=parent_id,
                response=response,
                db=db,
                responded_via="whatsapp",
            )
        except ValueError as e:
            return FlowResult(
                flow_complete=True,
                flow_data={},
                reply=build_text_payload(to, f"{e}\n\nReply 'menu' to continue."),
            )
        except Exception:
            logger.exception("Error recording permission slip response for %s", to)
            return FlowResult(
                flow_complete=True,
                flow_data={},
                reply=build_text_payload(
                    to, "Sorry, something went wrong. Reply 'menu' to continue."
                ),
            )

        confirmation = (
            "Thank you! Your consent has been recorded. ✓"
            if response == "yes"
            else "Understood. Your response has been recorded."
        )

        return FlowResult(
            flow_complete=True,
            flow_data={},
            reply=build_text_payload(to, confirmation),
        )

    return FlowResult(flow_complete=True, flow_data={})
