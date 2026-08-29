from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.flows import FlowResult
from app.models.conversation import Conversation
from app.services import notification_service, registration_service
from app.utils.whatsapp_helpers import (
    build_interactive_button_payload,
    build_interactive_list_payload,
    build_text_payload,
)

PREF_LABELS = {
    "class_reminders": "Class Reminders",
    "payment_reminders": "Payment Reminders",
    "marketing": "Marketing & Offers",
    "events": "Event Notifications",
    "progress_reports": "Progress Reports",
}


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

        prefs = await notification_service.get_or_create_preferences(
            parent.id, db
        )
        flow_data["parent_id"] = str(parent.id)

        status_lines = []
        for key, label in PREF_LABELS.items():
            enabled = getattr(prefs, key, False)
            icon = "ON" if enabled else "OFF"
            status_lines.append(f"  {label}: {icon}")

        body = (
            "*Your Notification Settings*\n\n"
            + "\n".join(status_lines)
            + "\n\nSelect a setting to toggle it:"
        )

        rows = [
            {
                "id": key,
                "title": label,
                "description": (
                    "Currently ON — tap to turn OFF"
                    if getattr(prefs, key, False)
                    else "Currently OFF — tap to turn ON"
                ),
            }
            for key, label in PREF_LABELS.items()
        ]

        return FlowResult(
            next_step="select_pref",
            flow_data=flow_data,
            reply=build_interactive_list_payload(
                to,
                header="Notifications",
                body=body,
                button_text="View Settings",
                rows=rows,
                section_title="Preferences",
            ),
        )

    if step == "select_pref":
        choice = user_input.strip()

        if choice not in PREF_LABELS:
            return FlowResult(
                next_step="select_pref",
                flow_data=flow_data,
                reply=build_text_payload(
                    to, "Please select a preference from the list."
                ),
            )

        parent_id_str = flow_data.get("parent_id")
        if not parent_id_str:
            return FlowResult(flow_complete=True, flow_data={})

        import uuid
        parent_id = uuid.UUID(parent_id_str)
        prefs = await notification_service.get_or_create_preferences(
            parent_id, db
        )

        current_value = getattr(prefs, choice, False)
        new_value = not current_value

        await notification_service.update_preferences(
            parent_id, {choice: new_value}, db
        )

        label = PREF_LABELS[choice]
        new_status = "ON" if new_value else "OFF"

        return FlowResult(
            next_step="after_toggle",
            flow_data=flow_data,
            reply=build_interactive_button_payload(
                to,
                body=f"*{label}* has been turned *{new_status}*.",
                buttons=[
                    {"id": "more_settings", "title": "More Settings"},
                    {"id": "back_menu", "title": "Main Menu"},
                ],
            ),
        )

    if step == "after_toggle":
        choice = user_input.strip().lower()

        if choice == "more_settings":
            return FlowResult(
                next_flow="notification_prefs",
                next_step="start",
                flow_data={},
            )

        return FlowResult(
            next_flow="main_menu",
            next_step="show",
            flow_data={},
        )

    return FlowResult(
        flow_complete=True,
        flow_data={},
        reply=build_text_payload(to, "Reply 'menu' to start over."),
    )
