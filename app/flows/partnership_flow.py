from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.flows import FlowResult
from app.models.conversation import Conversation
from app.services import analytics_service, referral_service
from app.utils.whatsapp_helpers import (
    build_interactive_button_payload,
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
        return FlowResult(
            next_step="school_name",
            flow_data=flow_data,
            reply=build_text_payload(
                to,
                "Thank you for your interest in partnering with EduConnect AI!\n\n"
                "We'd like to learn about your institution.\n\n"
                "What is the name of your school or institution?",
            ),
        )

    if step == "school_name":
        name = user_input.strip().title()
        if len(name) < 2:
            return FlowResult(
                next_step="school_name",
                flow_data=flow_data,
                reply=build_text_payload(to, "Please enter a valid school name."),
            )
        flow_data["school_name"] = name
        return FlowResult(
            next_step="contact_name",
            flow_data=flow_data,
            reply=build_text_payload(
                to, f"Great — *{name}*.\n\nWhat is your full name (contact person)?"
            ),
        )

    if step == "contact_name":
        name = user_input.strip().title()
        if len(name) < 2:
            return FlowResult(
                next_step="contact_name",
                flow_data=flow_data,
                reply=build_text_payload(to, "Please enter a valid name."),
            )
        flow_data["contact_name"] = name
        return FlowResult(
            next_step="contact_role",
            flow_data=flow_data,
            reply=build_text_payload(
                to, "What is your role at the school?\n(e.g., Principal, Director, Coordinator)"
            ),
        )

    if step == "contact_role":
        flow_data["contact_role"] = user_input.strip().title()
        return FlowResult(
            next_step="contact_email",
            flow_data=flow_data,
            reply=build_text_payload(
                to, "Please provide an email address for follow-up (or type 'skip'):"
            ),
        )

    if step == "contact_email":
        email = user_input.strip().lower()
        if email != "skip" and "@" in email:
            flow_data["contact_email"] = email
        return FlowResult(
            next_step="student_count",
            flow_data=flow_data,
            reply=build_text_payload(
                to,
                "Approximately how many students does your institution have?\n"
                "(e.g., 50, 200, 500+)",
            ),
        )

    if step == "student_count":
        flow_data["student_count"] = user_input.strip()
        return FlowResult(
            next_step="interest_area",
            flow_data=flow_data,
            reply=build_text_payload(
                to,
                "What areas of partnership interest you?\n\n"
                "For example:\n"
                "- After-school programmes\n"
                "- Holiday camps\n"
                "- Technology integration\n"
                "- Staff training\n"
                "- Other\n\n"
                "Please describe briefly:",
            ),
        )

    if step == "interest_area":
        flow_data["interest_area"] = user_input.strip()

        summary = (
            f"*Partnership Interest Summary*\n\n"
            f"School: {flow_data.get('school_name')}\n"
            f"Contact: {flow_data.get('contact_name')}\n"
            f"Role: {flow_data.get('contact_role')}\n"
            f"Email: {flow_data.get('contact_email', 'Not provided')}\n"
            f"Students: {flow_data.get('student_count')}\n"
            f"Interest: {flow_data.get('interest_area')}\n\n"
            f"Shall I submit this?"
        )
        return FlowResult(
            next_step="confirm",
            flow_data=flow_data,
            reply=build_interactive_button_payload(
                to,
                body=summary,
                buttons=[
                    {"id": "partner_submit", "title": "Submit"},
                    {"id": "partner_cancel", "title": "Cancel"},
                ],
                header="Review Details",
            ),
        )

    if step == "confirm":
        choice = user_input.strip().lower()
        if choice in ("partner_cancel", "cancel"):
            return FlowResult(
                flow_complete=True,
                flow_data={},
                reply=build_text_payload(
                    to, "No problem. Reply 'menu' anytime to start again."
                ),
            )

        referral = await referral_service.create_referral(
            referrer_type="partner",
            db=db,
            referrer_name=flow_data.get("contact_name"),
            referrer_whatsapp=to,
            referrer_email=flow_data.get("contact_email"),
            metadata={
                "school_name": flow_data.get("school_name"),
                "contact_role": flow_data.get("contact_role"),
                "student_count": flow_data.get("student_count"),
                "interest_area": flow_data.get("interest_area"),
                "source": "whatsapp_partnership_flow",
            },
        )

        await analytics_service.track_event(
            "partnership_lead",
            db,
            whatsapp_number=to,
            conversation_id=conversation.id,
            referral_code=referral.code,
            properties={
                "school_name": flow_data.get("school_name"),
                "student_count": flow_data.get("student_count"),
            },
        )

        return FlowResult(
            flow_complete=True,
            flow_data={},
            reply=build_text_payload(
                to,
                f"Your partnership interest has been submitted!\n\n"
                f"Reference: *{referral.code}*\n\n"
                f"Our partnerships team will reach out to you within "
                f"2 business days.\n\n"
                f"Reply 'menu' to return to the main menu.",
            ),
        )

    return FlowResult(
        flow_complete=True,
        flow_data={},
        reply=build_text_payload(to, "Reply 'menu' to start over."),
    )
