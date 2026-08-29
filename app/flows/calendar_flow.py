import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.flows import FlowResult
from app.models.conversation import Conversation
from app.services import calendar_service
from app.utils.whatsapp_helpers import (
    build_interactive_button_payload,
    build_text_payload,
)

logger = logging.getLogger(__name__)

CALENDAR_KEYWORDS = {"calendar", "term dates", "term start", "holidays", "school events"}


def _format_events(events) -> str:
    if not events:
        return "No upcoming events found."
    lines = []
    for event in events:
        lines.append(f"{event.emoji} *{event.title}*")
        lines.append(f"   {event.date_display}")
        if event.description:
            lines.append(f"   _{event.description}_")
        lines.append("")
    return "\n".join(lines).strip()


async def handle_step(
    step: str,
    user_input: str,
    flow_data: dict[str, Any],
    conversation: Conversation,
    db: AsyncSession,
) -> FlowResult:
    to = conversation.whatsapp_id

    if step == "start":
        events = await calendar_service.get_upcoming_events(db, days=30)
        event_text = _format_events(events)

        body = f"*Upcoming School Events (Next 30 Days)*\n\n{event_text}"

        if events:
            buttons = [
                {"id": "cal_week", "title": "Next 7 Days"},
                {"id": "cal_done", "title": "Done"},
            ]
            return FlowResult(
                next_step="after_calendar",
                flow_data=flow_data,
                reply=build_interactive_button_payload(
                    to,
                    body=body,
                    buttons=buttons,
                    header="Academic Calendar",
                ),
            )
        else:
            return FlowResult(
                flow_complete=True,
                flow_data={},
                reply=build_text_payload(
                    to,
                    "No upcoming events have been scheduled yet.\n\n"
                    "Reply 'menu' to see other options.",
                ),
            )

    if step == "after_calendar":
        choice = user_input.strip().lower()

        if choice == "cal_week":
            events = await calendar_service.get_next_7_days_events(db)
            event_text = _format_events(events)
            body = f"*Events in the Next 7 Days*\n\n{event_text}"
            return FlowResult(
                flow_complete=True,
                flow_data={},
                reply=build_text_payload(to, body),
            )

        return FlowResult(
            flow_complete=True,
            flow_data={},
        )

    return FlowResult(
        flow_complete=True,
        flow_data={},
        reply=build_text_payload(
            to, "Something went wrong. Reply 'menu' to start over."
        ),
    )
