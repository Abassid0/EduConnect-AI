from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.flows import FlowResult
from app.models.conversation import Conversation
from app.services import programme_service
from app.utils.whatsapp_helpers import (
    build_interactive_button_payload,
    build_interactive_list_payload,
    build_text_payload,
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
        programmes = await programme_service.get_active_programmes(db)
        if not programmes:
            return FlowResult(
                flow_complete=True,
                flow_data=flow_data,
                reply=build_text_payload(
                    to,
                    "No programmes are available right now. "
                    "Please check back soon!\n\nReply 'menu' for options.",
                ),
            )

        rows = [
            {
                "id": str(p.id),
                "title": p.name,
                "description": (
                    f"N{p.fee:,.0f} | "
                    f"Ages {p.age_range_min or '?'}-{p.age_range_max or '?'} | "
                    f"{p.available_slots} slots"
                ),
            }
            for p in programmes
        ]
        return FlowResult(
            next_step="view_programme",
            flow_data=flow_data,
            reply=build_interactive_list_payload(
                to,
                header="Our Programmes",
                body="Browse our available programmes below. Tap one for details.",
                button_text="View Programmes",
                rows=rows,
                section_title="Programmes",
            ),
        )

    if step == "view_programme":
        programme = await programme_service.get_programme_by_id(
            user_input.strip(), db
        )
        if not programme:
            return FlowResult(
                next_step="view_programme",
                flow_data=flow_data,
                reply=build_text_payload(
                    to, "Please select a programme from the list."
                ),
            )

        schedules = await programme_service.get_schedules_for_programme(
            programme.id, db
        )
        schedule_text = "\n".join(f"  - {s.display}" for s in schedules)
        if not schedule_text:
            schedule_text = "  Schedule TBA"

        age_range = ""
        if programme.age_range_min and programme.age_range_max:
            age_range = f"Ages: {programme.age_range_min}–{programme.age_range_max}\n"
        elif programme.age_range_min:
            age_range = f"Ages: {programme.age_range_min}+\n"

        details = (
            f"*{programme.name}*\n\n"
            f"{programme.description or ''}\n\n"
            f"Fee: N{programme.fee:,.0f} {programme.currency}\n"
            f"{age_range}"
            f"Level: {programme.level or 'All levels'}\n"
            f"Duration: {programme.duration or 'N/A'}\n"
            f"Mode: {programme.delivery_mode or 'N/A'}\n"
            f"Instructor: {programme.instructor or 'N/A'}\n"
            f"Available Slots: {programme.available_slots}\n\n"
            f"Schedule:\n{schedule_text}"
        )

        flow_data["viewed_programme_id"] = str(programme.id)
        flow_data["viewed_programme_name"] = programme.name

        return FlowResult(
            next_step="after_detail",
            flow_data=flow_data,
            reply=build_interactive_button_payload(
                to,
                body=details,
                buttons=[
                    {"id": "enrol_now", "title": "Register Now"},
                    {"id": "browse_more", "title": "Browse More"},
                    {"id": "back_menu", "title": "Main Menu"},
                ],
                header="Programme Details",
            ),
        )

    if step == "after_detail":
        choice = user_input.strip().lower()

        if choice == "enrol_now":
            return FlowResult(
                next_flow="registration",
                next_step="start",
                flow_data={},
            )

        if choice == "browse_more":
            return FlowResult(
                next_flow="enquiry",
                next_step="start",
                flow_data={},
            )

        if choice in ("back_menu", "menu"):
            return FlowResult(
                next_flow="main_menu",
                next_step="show",
                flow_data={},
            )

        return FlowResult(
            next_step="after_detail",
            flow_data=flow_data,
            reply=build_interactive_button_payload(
                to,
                body="What would you like to do?",
                buttons=[
                    {"id": "enrol_now", "title": "Register Now"},
                    {"id": "browse_more", "title": "Browse More"},
                    {"id": "back_menu", "title": "Main Menu"},
                ],
            ),
        )

    return FlowResult(
        flow_complete=True,
        flow_data={},
        reply=build_text_payload(to, "Reply 'menu' to start over."),
    )
