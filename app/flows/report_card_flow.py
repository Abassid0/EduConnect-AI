import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.flows import FlowResult
from app.models.conversation import Conversation
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

    if step == "start":
        try:
            from sqlalchemy import select
            from app.models.report_card import ReportCard
            from app.models.student import Student
            from app.services import report_card_service

            rc_id_str = flow_data.get("report_card_id", "")
            if not rc_id_str:
                return FlowResult(flow_complete=True, flow_data={})

            import uuid
            rc_id = uuid.UUID(rc_id_str)
            card = await report_card_service.get_report_card(rc_id, db)
            if not card:
                return FlowResult(flow_complete=True, flow_data={})

            student_result = await db.execute(select(Student).where(Student.id == card.student_id))
            student = student_result.scalar_one_or_none()
            student_name = student.full_name if student else ""

            body = report_card_service.format_report_card_message(card, student_name)
            button_id = f"report_card_ack_{rc_id_str}"

            return FlowResult(
                next_step="awaiting_acknowledgement",
                flow_data=flow_data,
                reply=build_interactive_button_payload(
                    to,
                    body=body,
                    buttons=[{"id": button_id, "title": "Acknowledge"}],
                    header="Report Card",
                ),
            )
        except Exception:
            logger.exception("Report card flow start error for %s", to)
            return FlowResult(flow_complete=True, flow_data={})

    if step == "awaiting_acknowledgement":
        choice = user_input.strip()
        rc_id_str = flow_data.get("report_card_id", "")

        if choice.startswith("report_card_ack_"):
            try:
                from sqlalchemy import select
                from app.models.parent import Parent
                from app.services import report_card_service

                parent_result = await db.execute(
                    select(Parent).where(Parent.whatsapp_number == to)
                )
                parent = parent_result.scalar_one_or_none()
                if parent and rc_id_str:
                    import uuid
                    await report_card_service.acknowledge(
                        uuid.UUID(rc_id_str), parent.id, db, via="whatsapp"
                    )

                return FlowResult(
                    flow_complete=True,
                    flow_data={},
                    reply=build_text_payload(to, "Thank you — received. ✓"),
                )
            except Exception:
                logger.exception("Report card acknowledgement error for %s", to)
                return FlowResult(
                    flow_complete=True,
                    flow_data={},
                    reply=build_text_payload(to, "Could not record acknowledgement. Reply 'menu' to continue."),
                )

        # Re-show the button for any other input
        try:
            from sqlalchemy import select
            from app.models.student import Student
            from app.services import report_card_service
            import uuid

            card = await report_card_service.get_report_card(uuid.UUID(rc_id_str), db)
            if card:
                student_result = await db.execute(select(Student).where(Student.id == card.student_id))
                student = student_result.scalar_one_or_none()
                body = report_card_service.format_report_card_message(card, student.full_name if student else "")
                return FlowResult(
                    next_step="awaiting_acknowledgement",
                    flow_data=flow_data,
                    reply=build_interactive_button_payload(
                        to,
                        body=body,
                        buttons=[{"id": f"report_card_ack_{rc_id_str}", "title": "Acknowledge"}],
                        header="Report Card",
                    ),
                )
        except Exception:
            logger.exception("Report card re-show error for %s", to)

        return FlowResult(flow_complete=True, flow_data={})

    return FlowResult(flow_complete=True, flow_data={})
