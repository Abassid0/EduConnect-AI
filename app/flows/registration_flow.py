import re
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.flows import FlowResult
from app.models.conversation import Conversation
from app.models.programme import CATEGORY_LABELS, PROGRAMME_CATEGORIES
from app.services import analytics_service, programme_service, referral_service, registration_service
from app.utils.whatsapp_helpers import (
    build_interactive_button_payload,
    build_interactive_list_payload,
    build_text_payload,
)

STEPS = [
    "start",
    "ask_referral",
    "parent_name",
    "child_name",
    "date_of_birth",
    "gender",
    "select_category",
    "select_programme",
    "select_programme_response",
    "select_schedule",
    "select_schedule_response",
    "parent_contact",
    "emergency_contact_name",
    "emergency_contact_phone",
    "consent",
    "summary_confirm",
]


async def handle_step(
    step: str,
    user_input: str,
    flow_data: dict[str, Any],
    conversation: Conversation,
    db: AsyncSession,
) -> FlowResult:
    to = conversation.whatsapp_id

    if step == "start":
        await analytics_service.track_event(
            "registration_start",
            db,
            whatsapp_number=to,
            conversation_id=conversation.id,
        )
        return FlowResult(
            next_step="ask_referral",
            flow_data=flow_data,
            reply=build_interactive_button_payload(
                to,
                body=(
                    "Let's register your child! I'll guide you through a few steps.\n\n"
                    "Do you have a referral code?"
                ),
                buttons=[
                    {"id": "ref_yes", "title": "Yes"},
                    {"id": "ref_no", "title": "No"},
                ],
            ),
        )

    if step == "ask_referral":
        choice = user_input.strip().lower()
        if choice == "ref_yes":
            return FlowResult(
                next_step="enter_referral",
                flow_data=flow_data,
                reply=build_text_payload(
                    to, "Please enter your referral code:"
                ),
            )
        flow_data["referral_code"] = None
        return FlowResult(
            next_step="parent_name",
            flow_data=flow_data,
            reply=build_text_payload(
                to,
                "No problem!\n\nWhat is your full name (parent/guardian)?",
            ),
        )

    if step == "enter_referral":
        code = user_input.strip().upper()
        referral = await referral_service.validate_referral_code(code, db)
        if referral:
            flow_data["referral_code"] = referral.code
            await analytics_service.track_event(
                "referral_used",
                db,
                whatsapp_number=to,
                conversation_id=conversation.id,
                referral_code=referral.code,
            )
            return FlowResult(
                next_step="parent_name",
                flow_data=flow_data,
                reply=build_text_payload(
                    to,
                    f"Referral code *{referral.code}* applied!\n\n"
                    "What is your full name (parent/guardian)?",
                ),
            )
        return FlowResult(
            next_step="parent_name",
            flow_data=flow_data,
            reply=build_text_payload(
                to,
                "That referral code wasn't found, but no worries — "
                "you can still register.\n\n"
                "What is your full name (parent/guardian)?",
            ),
        )

    if step == "parent_name":
        name = user_input.strip().title()
        if len(name) < 2:
            return FlowResult(
                next_step="parent_name",
                flow_data=flow_data,
                reply=build_text_payload(to, "Please enter a valid name."),
            )
        flow_data["parent_name"] = name
        return FlowResult(
            next_step="child_name",
            flow_data=flow_data,
            reply=build_text_payload(
                to,
                f"Thank you, {name}.\n\nWhat is the child's full name?",
            ),
        )

    if step == "child_name":
        name = user_input.strip().title()
        if len(name) < 2:
            return FlowResult(
                next_step="child_name",
                flow_data=flow_data,
                reply=build_text_payload(to, "Please enter a valid name."),
            )
        flow_data["child_name"] = name
        return FlowResult(
            next_step="date_of_birth",
            flow_data=flow_data,
            reply=build_text_payload(
                to,
                f"Got it — {name}.\n\n"
                "What is their date of birth? (e.g. 15/03/2016)",
            ),
        )

    if step == "date_of_birth":
        dob_str = user_input.strip()
        dob_match = re.match(r"(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})", dob_str)
        if not dob_match:
            return FlowResult(
                next_step="date_of_birth",
                flow_data=flow_data,
                reply=build_text_payload(
                    to,
                    "I couldn't read that date. Please use the format DD/MM/YYYY\n"
                    "Example: 15/03/2016",
                ),
            )
        flow_data["date_of_birth"] = dob_str
        return FlowResult(
            next_step="gender",
            flow_data=flow_data,
            reply=build_interactive_button_payload(
                to,
                body="What is the child's gender?",
                buttons=[
                    {"id": "male", "title": "Male"},
                    {"id": "female", "title": "Female"},
                ],
            ),
        )

    if step == "gender":
        gender = user_input.strip().lower()
        if gender not in ("male", "female"):
            return FlowResult(
                next_step="gender",
                flow_data=flow_data,
                reply=build_interactive_button_payload(
                    to,
                    body="Please select the child's gender:",
                    buttons=[
                        {"id": "male", "title": "Male"},
                        {"id": "female", "title": "Female"},
                    ],
                ),
            )
        flow_data["gender"] = gender.capitalize()

        rows = [
            {
                "id": f"cat_{cat}",
                "title": CATEGORY_LABELS[cat],
                "description": f"Programmes for {CATEGORY_LABELS[cat]}",
            }
            for cat in PROGRAMME_CATEGORIES
        ]
        return FlowResult(
            next_step="select_category",
            flow_data=flow_data,
            reply=build_interactive_list_payload(
                to,
                header="Choose Category",
                body="Which programme category would you like to register for?",
                button_text="View Categories",
                rows=rows,
                section_title="Categories",
            ),
        )

    if step == "select_category":
        category = user_input.strip().replace("cat_", "")
        if category not in PROGRAMME_CATEGORIES:
            rows = [
                {
                    "id": f"cat_{cat}",
                    "title": CATEGORY_LABELS[cat],
                    "description": f"Programmes for {CATEGORY_LABELS[cat]}",
                }
                for cat in PROGRAMME_CATEGORIES
            ]
            return FlowResult(
                next_step="select_category",
                flow_data=flow_data,
                reply=build_interactive_list_payload(
                    to,
                    header="Choose Category",
                    body="Please select a valid category from the list.",
                    button_text="View Categories",
                    rows=rows,
                    section_title="Categories",
                ),
            )

        flow_data["category"] = category
        programmes = await programme_service.get_active_programmes(
            db, category=category
        )

        if not programmes:
            return FlowResult(
                flow_complete=True,
                flow_data=flow_data,
                reply=build_text_payload(
                    to,
                    f"Sorry, no {CATEGORY_LABELS[category]} programmes are available. "
                    "Please check back later!",
                ),
            )

        rows = [
            {
                "id": str(p.id),
                "title": p.name,
                "description": f"N{p.fee:,.0f} | {p.level or 'All levels'}",
            }
            for p in programmes
        ]
        return FlowResult(
            next_step="select_programme_response",
            flow_data=flow_data,
            reply=build_interactive_list_payload(
                to,
                header="Choose a Programme",
                body=f"Select a {CATEGORY_LABELS[category]} programme to enrol in:",
                button_text="View Programmes",
                rows=rows,
                section_title="Available Programmes",
            ),
        )

    if step == "select_programme_response":
        programme = await programme_service.get_programme_by_id(
            user_input.strip(), db
        )
        if not programme:
            return FlowResult(
                next_step="select_programme_response",
                flow_data=flow_data,
                reply=build_text_payload(
                    to, "Please select a valid programme from the list."
                ),
            )
        flow_data["programme_id"] = str(programme.id)
        flow_data["programme_name"] = programme.name
        flow_data["programme_fee"] = str(programme.fee)

        schedules = await programme_service.get_schedules_for_programme(
            programme.id, db
        )
        if not schedules:
            flow_data["schedule_id"] = None
            return FlowResult(
                next_step="parent_contact",
                flow_data=flow_data,
                reply=build_text_payload(
                    to,
                    f"You selected *{programme.name}*.\n\n"
                    "No schedule slots configured yet — we'll assign one for you.\n\n"
                    "Now, please share your email address (or type 'skip'):",
                ),
            )

        rows = [
            {
                "id": str(s.id),
                "title": s.display,
                "description": programme.name[:72],
            }
            for s in schedules
        ]
        return FlowResult(
            next_step="select_schedule_response",
            flow_data=flow_data,
            reply=build_interactive_list_payload(
                to,
                header="Choose a Schedule",
                body=f"Pick a class time for *{programme.name}*:",
                button_text="View Schedules",
                rows=rows,
                section_title="Available Slots",
            ),
        )

    if step == "select_schedule_response":
        flow_data["schedule_id"] = user_input.strip()
        return FlowResult(
            next_step="parent_contact",
            flow_data=flow_data,
            reply=build_text_payload(
                to,
                "Great choice!\n\n"
                "Please share your email address (or type 'skip'):",
            ),
        )

    if step == "parent_contact":
        email = user_input.strip().lower()
        if email != "skip" and "@" in email:
            flow_data["parent_email"] = email
        return FlowResult(
            next_step="emergency_contact_name",
            flow_data=flow_data,
            reply=build_text_payload(
                to,
                "Who should we contact in case of emergency?\n\n"
                "Please enter their full name:",
            ),
        )

    if step == "emergency_contact_name":
        name = user_input.strip().title()
        if len(name) < 2:
            return FlowResult(
                next_step="emergency_contact_name",
                flow_data=flow_data,
                reply=build_text_payload(to, "Please enter a valid name."),
            )
        flow_data["emergency_contact_name"] = name
        return FlowResult(
            next_step="emergency_contact_phone",
            flow_data=flow_data,
            reply=build_text_payload(
                to,
                f"What is {name}'s phone number?",
            ),
        )

    if step == "emergency_contact_phone":
        phone = re.sub(r"[^\d+]", "", user_input.strip())
        if len(phone) < 10:
            return FlowResult(
                next_step="emergency_contact_phone",
                flow_data=flow_data,
                reply=build_text_payload(
                    to, "Please enter a valid phone number (at least 10 digits)."
                ),
            )
        flow_data["emergency_contact_phone"] = phone
        return FlowResult(
            next_step="consent",
            flow_data=flow_data,
            reply=build_interactive_button_payload(
                to,
                body=(
                    "Before we proceed, we need your consent to store "
                    "your child's information for registration and class management.\n\n"
                    "Do you agree?"
                ),
                buttons=[
                    {"id": "consent_yes", "title": "Yes, I agree"},
                    {"id": "consent_no", "title": "No, cancel"},
                ],
                header="Data Consent",
            ),
        )

    if step == "consent":
        choice = user_input.strip().lower()
        if choice in ("consent_no", "no", "cancel"):
            return FlowResult(
                flow_complete=True,
                flow_data={},
                reply=build_text_payload(
                    to,
                    "No problem. Registration has been cancelled.\n\n"
                    "Reply 'menu' anytime to start again.",
                ),
            )
        if choice not in ("consent_yes", "yes", "agree"):
            return FlowResult(
                next_step="consent",
                flow_data=flow_data,
                reply=build_interactive_button_payload(
                    to,
                    body="Please confirm your consent:",
                    buttons=[
                        {"id": "consent_yes", "title": "Yes, I agree"},
                        {"id": "consent_no", "title": "No, cancel"},
                    ],
                ),
            )
        flow_data["consent"] = True

        programme_name = flow_data.get("programme_name", "N/A")
        fee = flow_data.get("programme_fee", "N/A")
        category_label = CATEGORY_LABELS.get(flow_data.get("category", ""), "")
        category_line = f"Category: {category_label}\n" if category_label else ""
        summary = (
            f"*Registration Summary*\n\n"
            f"Parent: {flow_data.get('parent_name', 'N/A')}\n"
            f"Child: {flow_data.get('child_name', 'N/A')}\n"
            f"DOB: {flow_data.get('date_of_birth', 'N/A')}\n"
            f"Gender: {flow_data.get('gender', 'N/A')}\n"
            f"{category_line}"
            f"Programme: {programme_name}\n"
            f"Fee: N{float(fee):,.0f}\n"
            f"Emergency Contact: {flow_data.get('emergency_contact_name', 'N/A')} "
            f"({flow_data.get('emergency_contact_phone', 'N/A')})\n\n"
            f"Is everything correct?"
        )
        return FlowResult(
            next_step="summary_confirm",
            flow_data=flow_data,
            reply=build_interactive_button_payload(
                to,
                body=summary,
                buttons=[
                    {"id": "confirm_yes", "title": "Confirm"},
                    {"id": "confirm_edit", "title": "Start Over"},
                    {"id": "confirm_cancel", "title": "Cancel"},
                ],
                header="Please Review",
            ),
        )

    if step == "summary_confirm":
        choice = user_input.strip().lower()

        if choice in ("confirm_cancel", "cancel"):
            return FlowResult(
                flow_complete=True,
                flow_data={},
                reply=build_text_payload(
                    to,
                    "Registration cancelled.\n\nReply 'menu' to start again.",
                ),
            )

        if choice in ("confirm_edit", "edit", "start over"):
            return FlowResult(
                next_flow="registration",
                next_step="start",
                flow_data={},
            )

        if choice in ("confirm_yes", "yes", "confirm", "1"):
            student, enrollment = await registration_service.create_registration(
                flow_data=flow_data,
                whatsapp_number=conversation.whatsapp_id,
                db=db,
            )
            flow_data["registered_student_id"] = str(student.id)
            flow_data["registered_enrollment_id"] = str(enrollment.id)

            referral_code = flow_data.get("referral_code")
            if referral_code:
                referral = await referral_service.get_referral_by_code(referral_code, db)
                if referral:
                    from decimal import Decimal
                    await referral_service.record_referral_registration(
                        referral, Decimal(flow_data.get("programme_fee", "0")), db
                    )

            await analytics_service.track_event(
                "registration_complete",
                db,
                whatsapp_number=to,
                parent_id=student.parent_id,
                student_id=student.id,
                conversation_id=conversation.id,
                referral_code=referral_code,
                properties={
                    "programme": flow_data.get("programme_name"),
                    "student_name": student.full_name,
                },
            )

            return FlowResult(
                next_step="post_registration",
                flow_data=flow_data,
                reply=build_interactive_button_payload(
                    to,
                    body=(
                        f"Registration complete!\n\n"
                        f"Registration ID: *{student.registration_id}*\n"
                        f"Student: {student.full_name}\n"
                        f"Programme: {flow_data.get('programme_name')}\n\n"
                        "Would you like to pay now?"
                    ),
                    buttons=[
                        {"id": "pay_now_reg", "title": "Pay Now"},
                        {"id": "back_menu_reg", "title": "Main Menu"},
                    ],
                    header="Registration Done",
                ),
            )

        return FlowResult(
            next_step="summary_confirm",
            flow_data=flow_data,
            reply=build_interactive_button_payload(
                to,
                body="Please confirm, edit, or cancel your registration:",
                buttons=[
                    {"id": "confirm_yes", "title": "Confirm"},
                    {"id": "confirm_edit", "title": "Start Over"},
                    {"id": "confirm_cancel", "title": "Cancel"},
                ],
            ),
        )

    if step == "post_registration":
        choice = user_input.strip().lower()
        if choice == "pay_now_reg":
            return FlowResult(
                next_flow="payment",
                next_step="start",
                flow_data={
                    "from_registration": True,
                    "pre_student_id": flow_data.get("registered_student_id"),
                    "pre_enrollment_id": flow_data.get("registered_enrollment_id"),
                },
            )
        return FlowResult(
            next_flow="main_menu",
            next_step="show",
            flow_data={},
        )

    return FlowResult(
        flow_complete=True,
        flow_data={},
        reply=build_text_payload(to, "Something went wrong. Reply 'menu' to start over."),
    )
