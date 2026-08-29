from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.flows import FlowResult
from app.models.conversation import Conversation
from app.services import programme_service, registration_service
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

        students = await registration_service.get_students_for_parent(parent.id, db)
        if not students:
            return FlowResult(
                flow_complete=True,
                flow_data={},
                reply=build_text_payload(
                    to,
                    "No students registered under your account yet.\n\n"
                    "Reply 'menu' to register a student.",
                ),
            )

        flow_data["parent_id"] = str(parent.id)
        rows = [
            {
                "id": str(s.id),
                "title": s.full_name,
                "description": f"ID: {s.registration_id} | {s.status}",
            }
            for s in students
        ]

        return FlowResult(
            next_step="select_student",
            flow_data=flow_data,
            reply=build_interactive_list_payload(
                to,
                header="Your Children",
                body=f"You have {len(students)} registered student(s). "
                     "Tap one to see their details and classes.",
                button_text="View Students",
                rows=rows,
                section_title="Students",
            ),
        )

    if step == "select_student":
        student_id = user_input.strip()
        parent = await registration_service.get_parent_by_whatsapp(to, db)
        if not parent:
            return FlowResult(flow_complete=True, flow_data={})

        students = await registration_service.get_students_for_parent(parent.id, db)
        student = next((s for s in students if str(s.id) == student_id), None)

        if not student:
            return FlowResult(
                next_step="select_student",
                flow_data=flow_data,
                reply=build_text_payload(to, "Please select a student from the list."),
            )

        enrollments = await registration_service.get_enrollments_for_student(
            student.id, db
        )

        if not enrollments:
            info = (
                f"*{student.full_name}*\n"
                f"Registration ID: {student.registration_id}\n"
                f"Status: {student.status}\n\n"
                "No active enrolments."
            )
        else:
            enrolment_lines = []
            for e in enrollments:
                programme = await programme_service.get_programme_by_id(
                    e.programme_id, db
                )
                prog_name = programme.name if programme else "Unknown"
                schedule_text = ""
                if e.schedule_id and programme:
                    schedules = await programme_service.get_schedules_for_programme(
                        programme.id, db
                    )
                    sched = next(
                        (s for s in schedules if s.id == e.schedule_id), None
                    )
                    if sched:
                        schedule_text = f" | {sched.display}"
                enrolment_lines.append(
                    f"  - {prog_name} ({e.status}){schedule_text}"
                )

            info = (
                f"*{student.full_name}*\n"
                f"Registration ID: {student.registration_id}\n"
                f"DOB: {student.date_of_birth or 'N/A'}\n"
                f"Status: {student.status}\n\n"
                f"Enrolments:\n" + "\n".join(enrolment_lines)
            )

        flow_data["selected_student_id"] = student_id

        return FlowResult(
            next_step="student_action",
            flow_data=flow_data,
            reply=build_interactive_button_payload(
                to,
                body=info,
                buttons=[
                    {"id": "view_another", "title": "View Another"},
                    {"id": "back_menu", "title": "Main Menu"},
                ],
                header="Student Details",
            ),
        )

    if step == "student_action":
        choice = user_input.strip().lower()

        if choice == "view_another":
            return FlowResult(
                next_flow="my_account",
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
