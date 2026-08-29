from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.flows import FlowResult
from app.models.conversation import Conversation
from app.services import escalation_service, registration_service, support_service
from app.services.admin_notify import notify_human_agent_request, notify_new_ticket
from app.utils.whatsapp_helpers import (
    build_interactive_button_payload,
    build_interactive_list_payload,
    build_text_payload,
)

DEPARTMENT_OPTIONS = [
    {"id": "dept_admissions", "title": "Admissions", "description": "Registration & enrollment help"},
    {"id": "dept_payments", "title": "Payments & Billing", "description": "Fees, receipts, refunds"},
    {"id": "dept_academic", "title": "Academic", "description": "Classes, schedules, curriculum"},
    {"id": "dept_technical", "title": "Technical Support", "description": "App issues, login problems"},
    {"id": "dept_general", "title": "General Enquiry", "description": "Other questions"},
]

DEPT_MAP = {
    "dept_admissions": "admissions",
    "dept_payments": "payments",
    "dept_academic": "academic",
    "dept_technical": "technical",
    "dept_general": "general",
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
        return FlowResult(
            next_step="select_department",
            flow_data=flow_data,
            reply=build_interactive_list_payload(
                to,
                header="Get Help",
                body=(
                    "We're here to help! Please select the department "
                    "that best matches your enquiry."
                ),
                button_text="Choose Department",
                rows=DEPARTMENT_OPTIONS,
                section_title="Departments",
            ),
        )

    if step == "select_department":
        dept = DEPT_MAP.get(user_input.strip())
        if not dept:
            return FlowResult(
                next_step="select_department",
                flow_data=flow_data,
                reply=build_text_payload(
                    to, "Please select a department from the list."
                ),
            )

        flow_data["department"] = dept
        return FlowResult(
            next_step="describe_issue",
            flow_data=flow_data,
            reply=build_text_payload(
                to,
                "Please describe your issue in a few words.\n\n"
                "For example: _I need help with my payment receipt_",
            ),
        )

    if step == "describe_issue":
        description = user_input.strip()
        if len(description) < 3:
            return FlowResult(
                next_step="describe_issue",
                flow_data=flow_data,
                reply=build_text_payload(
                    to, "Please provide a bit more detail about your issue."
                ),
            )

        flow_data["description"] = description
        return FlowResult(
            next_step="confirm_or_agent",
            flow_data=flow_data,
            reply=build_interactive_button_payload(
                to,
                body=(
                    f"*Department:* {flow_data['department'].title()}\n"
                    f"*Issue:* {description}\n\n"
                    "Would you like to create a support ticket, "
                    "or speak with a human agent right away?"
                ),
                buttons=[
                    {"id": "create_ticket", "title": "Create Ticket"},
                    {"id": "human_agent", "title": "Human Agent"},
                    {"id": "cancel_support", "title": "Cancel"},
                ],
            ),
        )

    if step == "confirm_or_agent":
        choice = user_input.strip().lower()

        if choice == "cancel_support":
            return FlowResult(
                next_flow="main_menu",
                next_step="show",
                flow_data={},
            )

        parent = await registration_service.get_parent_by_whatsapp(to, db)
        parent_id = parent.id if parent else None

        if choice == "human_agent":
            ticket = await escalation_service.escalate(
                conversation_id=conversation.id,
                whatsapp_number=to,
                reason="human_request",
                db=db,
                description=flow_data.get("description"),
                parent_id=parent_id,
            )
            await notify_human_agent_request(
                ticket_number=ticket.ticket_number,
                department=ticket.department,
                priority=ticket.priority,
                subject=ticket.subject,
                user_id=to,
            )
            return FlowResult(
                flow_complete=True,
                flow_data={},
                reply=build_text_payload(
                    to,
                    f"You've been connected to our support team.\n"
                    f"Ticket: *{ticket.ticket_number}*\n\n"
                    f"A support agent will reply in this chat shortly.\n"
                    f"Reply *menu* when you're done to return to the bot.",
                ),
            )

        ticket = await support_service.create_ticket(
            subject=flow_data.get("description", "Support request")[:300],
            db=db,
            description=flow_data.get("description"),
            department=flow_data.get("department", "general"),
            conversation_id=conversation.id,
            parent_id=parent_id,
            whatsapp_number=to,
        )

        await notify_new_ticket(
            ticket_number=ticket.ticket_number,
            department=ticket.department,
            priority=ticket.priority,
            subject=ticket.subject,
            user_id=to,
        )

        return FlowResult(
            flow_complete=True,
            flow_data={},
            reply=build_text_payload(
                to,
                f"Your support ticket has been created!\n\n"
                f"Ticket: *{ticket.ticket_number}*\n"
                f"Department: {ticket.department.title()}\n"
                f"Priority: {ticket.priority.title()}\n\n"
                f"Our team will review your request and get back to you.\n"
                f"Reply *menu* to return to the main menu.",
            ),
        )

    return FlowResult(
        flow_complete=True,
        flow_data={},
        reply=build_text_payload(to, "Reply 'menu' to start over."),
    )
