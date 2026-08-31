from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.flows import FlowResult
from app.models.conversation import Conversation
from app.models.programme import (
    CATEGORY_LABELS,
    LEVEL_LABELS,
    PROGRAMME_CATEGORIES,
    TRACK_LABELS,
)
from app.services import billing_service, programme_service
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
        rows = [
            {
                "id": f"cat_{cat}",
                "title": CATEGORY_LABELS[cat],
                "description": f"View {CATEGORY_LABELS[cat]} programmes",
            }
            for cat in PROGRAMME_CATEGORIES
        ]
        return FlowResult(
            next_step="select_category",
            flow_data=flow_data,
            reply=build_interactive_list_payload(
                to,
                header="Our Programmes",
                body="Which category of programmes are you interested in?",
                button_text="View Categories",
                rows=rows,
                section_title="Programme Categories",
            ),
        )

    if step == "select_category":
        category = user_input.strip().replace("cat_", "")
        if category not in PROGRAMME_CATEGORIES:
            rows = [
                {
                    "id": f"cat_{cat}",
                    "title": CATEGORY_LABELS[cat],
                    "description": f"View {CATEGORY_LABELS[cat]} programmes",
                }
                for cat in PROGRAMME_CATEGORIES
            ]
            return FlowResult(
                next_step="select_category",
                flow_data=flow_data,
                reply=build_interactive_list_payload(
                    to,
                    header="Our Programmes",
                    body="Please select a valid category from the list.",
                    button_text="View Categories",
                    rows=rows,
                    section_title="Programme Categories",
                ),
            )

        flow_data["category"] = category
        programmes = await programme_service.get_active_programmes(
            db, category=category
        )

        if not programmes:
            return FlowResult(
                next_step="start",
                flow_data=flow_data,
                reply=build_text_payload(
                    to,
                    f"No {CATEGORY_LABELS[category]} programmes are available "
                    "right now. Please try another category.\n\n"
                    "Reply 'menu' for options.",
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
                header=f"{CATEGORY_LABELS[category]} Programmes",
                body=f"Browse our {CATEGORY_LABELS[category]} programmes below.",
                button_text="View Programmes",
                rows=rows,
                section_title="Programmes",
            ),
        )

    if step == "view_programme":
        try:
            programme = await programme_service.get_programme_by_id(
                user_input.strip(), db
            )
        except Exception:
            programme = None
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

        category_line = f"Category: {CATEGORY_LABELS.get(programme.category, programme.category)}\n"
        level_line = f"Level: {LEVEL_LABELS.get(programme.level, programme.level) if programme.level else 'All levels'}\n"
        track_line = (
            f"Track: {TRACK_LABELS.get(programme.track, programme.track)}\n"
            if programme.track
            else ""
        )

        fee_section = f"Fee: N{programme.fee:,.0f} {programme.currency}\n"
        fee_items = await billing_service.list_programme_fee_items(
            programme.id, db, term="first"
        )
        if fee_items:
            fee_lines = []
            mandatory_total = sum(
                fi.amount for fi in fee_items if not fi.is_optional
            )
            for fi in fee_items:
                tag = " _(Optional)_" if fi.is_optional else ""
                fee_lines.append(f"  - {fi.fee_type.name}: N{fi.amount:,.0f}{tag}")
            fee_section = (
                f"*Fee Breakdown (1st Term):*\n"
                + "\n".join(fee_lines)
                + f"\n*Total: N{mandatory_total:,.0f}*\n"
            )

        details = (
            f"*{programme.name}*\n\n"
            f"{programme.description or ''}\n\n"
            f"{fee_section}"
            f"{age_range}"
            f"{category_line}"
            f"{level_line}"
            f"{track_line}"
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
