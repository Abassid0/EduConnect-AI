import logging
import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.flows import FlowResult
from app.models.conversation import Conversation
from app.services import (
    analytics_service,
    billing_service,
    payment_service,
    programme_service,
    registration_service,
)
from app.utils.whatsapp_helpers import (
    build_interactive_button_payload,
    build_interactive_list_payload,
    build_text_payload,
)

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
        if flow_data.get("from_registration"):
            return await _handle_from_registration(flow_data, to, db)

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

        students = await registration_service.get_students_for_parent(
            parent.id, db
        )
        if not students:
            return FlowResult(
                flow_complete=True,
                flow_data={},
                reply=build_text_payload(
                    to,
                    "No students registered yet.\n\n"
                    "Reply 'menu' to register a student.",
                ),
            )

        flow_data["parent_id"] = str(parent.id)
        flow_data["parent_email"] = parent.email

        if len(students) == 1:
            student = students[0]
            flow_data["student_id"] = str(student.id)
            flow_data["student_name"] = student.full_name
            return await _build_unified_payables(flow_data, to, student.id, parent.id, db)

        rows = [
            {
                "id": str(s.id),
                "title": s.full_name,
                "description": f"ID: {s.registration_id}",
            }
            for s in students
        ]
        return FlowResult(
            next_step="select_student",
            flow_data=flow_data,
            reply=build_interactive_list_payload(
                to,
                header="Select Student",
                body="Which student would you like to make a payment for?",
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

        students = await registration_service.get_students_for_parent(
            parent.id, db
        )
        student = next(
            (s for s in students if str(s.id) == student_id), None
        )
        if not student:
            return FlowResult(
                next_step="select_student",
                flow_data=flow_data,
                reply=build_text_payload(
                    to, "Please select a student from the list."
                ),
            )

        flow_data["student_id"] = str(student.id)
        flow_data["student_name"] = student.full_name
        conversation.selected_student_id = student.id
        return await _build_unified_payables(flow_data, to, student.id, parent.id, db)

    if step == "select_payable":
        return await _handle_payable_selection(user_input, flow_data, to, db)

    if step == "enter_amount":
        return await _handle_partial_amount(user_input, flow_data, to, db)

    if step == "confirm_payment":
        return await _handle_confirm_payment(user_input, flow_data, to, conversation, db)

    return FlowResult(
        flow_complete=True,
        flow_data={},
        reply=build_text_payload(
            to, "Something went wrong. Reply 'menu' to start over."
        ),
    )


async def _handle_from_registration(
    flow_data: dict[str, Any],
    to: str,
    db: AsyncSession,
) -> FlowResult:
    student_id = uuid.UUID(flow_data["pre_student_id"])
    enrollment_id = uuid.UUID(flow_data["pre_enrollment_id"])

    pending = await payment_service.get_pending_enrollments(student_id, db)
    enrollment = next(
        (e for e in pending if e.id == enrollment_id), None
    )

    if not enrollment:
        return FlowResult(
            flow_complete=True,
            flow_data={},
            reply=build_text_payload(
                to,
                "No pending payment found for this enrollment.\n\n"
                "Reply 'menu' to see options.",
            ),
        )

    programme = await programme_service.get_programme_by_id(
        enrollment.programme_id, db
    )
    if not programme:
        return FlowResult(
            flow_complete=True,
            flow_data={},
            reply=build_text_payload(
                to, "Programme not found. Reply 'menu' to start over."
            ),
        )

    parent = await registration_service.get_parent_by_whatsapp(to, db)
    students = await registration_service.get_students_for_parent(parent.id, db)
    student = next((s for s in students if s.id == student_id), None)

    new_flow_data = {
        "student_id": str(student_id),
        "student_name": student.full_name if student else "N/A",
        "enrollment_id": str(enrollment_id),
        "programme_id": str(programme.id),
        "programme_name": programme.name,
        "payment_amount": str(programme.fee),
        "parent_email": parent.email if parent else None,
        "payable_type": "enrollment",
    }

    return FlowResult(
        next_step="confirm_payment",
        flow_data=new_flow_data,
        reply=build_interactive_button_payload(
            to,
            body=(
                f"*Payment Summary*\n\n"
                f"Student: {new_flow_data['student_name']}\n"
                f"Programme: {programme.name}\n"
                f"Amount: N{programme.fee:,.0f}\n\n"
                "Proceed to payment?"
            ),
            buttons=[
                {"id": "pay_now", "title": "Pay Now"},
                {"id": "pay_cancel", "title": "Cancel"},
            ],
            header="Confirm Payment",
        ),
    )


async def _build_unified_payables(
    flow_data: dict[str, Any],
    to: str,
    student_id: uuid.UUID,
    parent_id: uuid.UUID,
    db: AsyncSession,
) -> FlowResult:
    """Build a unified list of pending enrollments and outstanding invoices."""
    pending_enrollments = await payment_service.get_pending_enrollments(student_id, db)
    outstanding_invoices = await billing_service.get_outstanding_invoices(parent_id, db)
    student_invoices = [
        inv for inv in outstanding_invoices
        if inv.student_id == student_id or inv.student_id is None
    ]

    rows = []
    payable_map = {}

    for e in pending_enrollments:
        programme = await programme_service.get_programme_by_id(e.programme_id, db)
        prog_name = programme.name if programme else "Unknown"
        fee = programme.fee if programme else Decimal("0")
        item_id = f"enr_{e.id}"
        rows.append({
            "id": item_id,
            "title": prog_name[:24],
            "description": f"Enrollment — N{fee:,.0f}",
        })
        payable_map[item_id] = {
            "type": "enrollment",
            "enrollment_id": str(e.id),
            "programme_id": str(e.programme_id) if e.programme_id else None,
            "name": prog_name,
            "amount": str(fee),
        }

    for inv in student_invoices:
        remaining = inv.total_amount - inv.amount_paid
        item_id = f"inv_{inv.id}"
        status_label = "Partial" if inv.status == "partial" else "Due"
        if inv.status == "overdue":
            status_label = "OVERDUE"
        rows.append({
            "id": item_id,
            "title": inv.title[:24],
            "description": f"{status_label} — N{remaining:,.0f}",
        })
        payable_map[item_id] = {
            "type": "invoice",
            "invoice_id": str(inv.id),
            "invoice_number": inv.invoice_number,
            "name": inv.title,
            "total_amount": str(inv.total_amount),
            "amount_paid": str(inv.amount_paid),
            "remaining": str(remaining),
        }

    if not rows:
        return FlowResult(
            flow_complete=True,
            flow_data={},
            reply=build_text_payload(
                to,
                f"No pending payments for {flow_data.get('student_name', 'this student')}. "
                "All fees are up to date!\n\n"
                "Reply 'menu' to see options.",
            ),
        )

    flow_data["payable_map"] = payable_map

    if len(rows) == 1:
        only_id = rows[0]["id"]
        return await _handle_payable_selection(only_id, flow_data, to, db)

    total_due = sum(
        Decimal(p.get("amount", "0")) if p["type"] == "enrollment"
        else Decimal(p.get("remaining", "0"))
        for p in payable_map.values()
    )

    return FlowResult(
        next_step="select_payable",
        flow_data=flow_data,
        reply=build_interactive_list_payload(
            to,
            header="Outstanding Fees",
            body=(
                f"{flow_data['student_name']} has {len(rows)} pending payment(s).\n"
                f"Total Outstanding: N{total_due:,.0f}\n\n"
                "Select one to pay:"
            ),
            button_text="View Fees",
            rows=rows[:10],
            section_title="Payments Due",
        ),
    )


async def _handle_payable_selection(
    user_input: str,
    flow_data: dict[str, Any],
    to: str,
    db: AsyncSession,
) -> FlowResult:
    payable_map = flow_data.get("payable_map", {})
    selected = payable_map.get(user_input.strip())

    if not selected:
        return FlowResult(
            next_step="select_payable",
            flow_data=flow_data,
            reply=build_text_payload(
                to, "Please select a fee from the list."
            ),
        )

    if selected["type"] == "enrollment":
        programme = await programme_service.get_programme_by_id(
            uuid.UUID(selected["programme_id"]), db
        )
        if not programme:
            return FlowResult(
                flow_complete=True,
                flow_data={},
                reply=build_text_payload(
                    to, "Programme not found. Reply 'menu' to start over."
                ),
            )

        flow_data["payable_type"] = "enrollment"
        flow_data["enrollment_id"] = selected["enrollment_id"]
        flow_data["programme_id"] = selected["programme_id"]
        flow_data["programme_name"] = programme.name
        flow_data["payment_amount"] = str(programme.fee)

        return FlowResult(
            next_step="confirm_payment",
            flow_data=flow_data,
            reply=build_interactive_button_payload(
                to,
                body=(
                    f"*Payment Summary*\n\n"
                    f"Student: {flow_data['student_name']}\n"
                    f"Programme: {programme.name}\n"
                    f"Amount: N{programme.fee:,.0f}\n\n"
                    "Proceed to payment?"
                ),
                buttons=[
                    {"id": "pay_now", "title": "Pay Now"},
                    {"id": "pay_cancel", "title": "Cancel"},
                ],
                header="Confirm Payment",
            ),
        )

    remaining = Decimal(selected["remaining"])
    flow_data["payable_type"] = "invoice"
    flow_data["invoice_id"] = selected["invoice_id"]
    flow_data["invoice_number"] = selected["invoice_number"]
    flow_data["invoice_name"] = selected["name"]
    flow_data["invoice_remaining"] = selected["remaining"]

    buttons = [
        {"id": "pay_full", "title": f"Pay N{remaining:,.0f}"},
        {"id": "pay_partial", "title": "Pay Part"},
        {"id": "pay_cancel", "title": "Cancel"},
    ]

    return FlowResult(
        next_step="confirm_payment",
        flow_data=flow_data,
        reply=build_interactive_button_payload(
            to,
            body=(
                f"*Invoice: {selected['invoice_number']}*\n"
                f"{selected['name']}\n\n"
                f"Student: {flow_data['student_name']}\n"
                f"Total: N{Decimal(selected['total_amount']):,.0f}\n"
                f"Already Paid: N{Decimal(selected['amount_paid']):,.0f}\n"
                f"Remaining: N{remaining:,.0f}\n\n"
                "How would you like to pay?"
            ),
            buttons=buttons,
            header="Invoice Payment",
        ),
    )


async def _handle_partial_amount(
    user_input: str,
    flow_data: dict[str, Any],
    to: str,
    db: AsyncSession,
) -> FlowResult:
    remaining = Decimal(flow_data["invoice_remaining"])

    try:
        amount = Decimal(user_input.strip().replace(",", "").replace("N", "").replace("n", ""))
    except Exception:
        return FlowResult(
            next_step="enter_amount",
            flow_data=flow_data,
            reply=build_text_payload(
                to,
                f"Please enter a valid amount (e.g. 5000).\n"
                f"Remaining balance: N{remaining:,.0f}",
            ),
        )

    if amount <= 0:
        return FlowResult(
            next_step="enter_amount",
            flow_data=flow_data,
            reply=build_text_payload(to, "Amount must be greater than zero."),
        )

    if amount > remaining:
        return FlowResult(
            next_step="enter_amount",
            flow_data=flow_data,
            reply=build_text_payload(
                to,
                f"Amount cannot exceed the remaining balance of N{remaining:,.0f}.\n"
                "Enter a smaller amount:",
            ),
        )

    flow_data["payment_amount"] = str(amount)
    return FlowResult(
        next_step="confirm_payment",
        flow_data=flow_data,
        reply=build_interactive_button_payload(
            to,
            body=(
                f"*Partial Payment*\n\n"
                f"Invoice: {flow_data['invoice_number']}\n"
                f"{flow_data['invoice_name']}\n"
                f"Amount to Pay: N{amount:,.0f}\n"
                f"(Remaining after: N{remaining - amount:,.0f})\n\n"
                "Proceed?"
            ),
            buttons=[
                {"id": "pay_now", "title": "Pay Now"},
                {"id": "pay_cancel", "title": "Cancel"},
            ],
            header="Confirm Payment",
        ),
    )


async def _handle_confirm_payment(
    user_input: str,
    flow_data: dict[str, Any],
    to: str,
    conversation: Conversation,
    db: AsyncSession,
) -> FlowResult:
    choice = user_input.strip().lower()

    if choice in ("pay_cancel", "cancel"):
        return FlowResult(
            flow_complete=True,
            flow_data={},
            reply=build_text_payload(
                to,
                "Payment cancelled.\n\nReply 'menu' to see options.",
            ),
        )

    if choice == "pay_partial":
        remaining = Decimal(flow_data.get("invoice_remaining", "0"))
        return FlowResult(
            next_step="enter_amount",
            flow_data=flow_data,
            reply=build_text_payload(
                to,
                f"Enter the amount you'd like to pay.\n"
                f"Outstanding balance: N{remaining:,.0f}\n\n"
                "Type the amount (e.g. 5000):",
            ),
        )

    if choice == "pay_full":
        flow_data["payment_amount"] = flow_data.get("invoice_remaining", "0")
        choice = "pay_now"

    if choice not in ("pay_now", "pay", "yes"):
        return FlowResult(
            next_step="confirm_payment",
            flow_data=flow_data,
            reply=build_interactive_button_payload(
                to,
                body="Would you like to proceed with payment?",
                buttons=[
                    {"id": "pay_now", "title": "Pay Now"},
                    {"id": "pay_cancel", "title": "Cancel"},
                ],
            ),
        )

    payable_type = flow_data.get("payable_type", "enrollment")

    try:
        if payable_type == "invoice":
            payment = await billing_service.create_invoice_payment(
                invoice_id=uuid.UUID(flow_data["invoice_id"]),
                amount=Decimal(flow_data["payment_amount"]),
                whatsapp_number=to,
                db=db,
                email=flow_data.get("parent_email"),
            )
        else:
            payment = await payment_service.create_payment(
                student_id=uuid.UUID(flow_data["student_id"]),
                enrollment_id=uuid.UUID(flow_data["enrollment_id"]),
                programme_id=uuid.UUID(flow_data["programme_id"]),
                amount=Decimal(flow_data["payment_amount"]),
                currency="NGN",
                whatsapp_number=to,
                metadata={
                    "student_name": flow_data.get("student_name"),
                    "programme_name": flow_data.get("programme_name"),
                },
                db=db,
            )
            payment = await payment_service.initialize_paystack_transaction(
                payment=payment,
                email=flow_data.get("parent_email"),
                db=db,
            )

        flow_data["payment_reference"] = payment.reference

        await analytics_service.track_event(
            "payment_init",
            db,
            whatsapp_number=to,
            conversation_id=conversation.id,
            properties={
                "amount": str(payment.amount),
                "reference": payment.reference,
                "type": payable_type,
            },
        )

        label = flow_data.get("programme_name") or flow_data.get("invoice_name", "Fee")

        return FlowResult(
            flow_complete=True,
            flow_data={},
            reply=build_text_payload(
                to,
                f"Your payment link is ready!\n\n"
                f"Click here to pay:\n{payment.paystack_authorization_url}\n\n"
                f"Description: {label}\n"
                f"Amount: N{payment.amount:,.0f}\n"
                f"Reference: {payment.reference}\n\n"
                "The link is valid for 24 hours. Once you "
                "complete payment, you'll receive a receipt "
                "here.\n\n"
                "Reply 'menu' to return to the main menu.",
            ),
        )

    except ValueError as e:
        return FlowResult(
            flow_complete=True,
            flow_data={},
            reply=build_text_payload(
                to,
                f"Payment error: {e}\n\n"
                "Reply 'menu' to return to the main menu.",
            ),
        )
    except Exception:
        logger.exception("Payment initialization failed for %s", to)
        return FlowResult(
            flow_complete=True,
            flow_data={},
            reply=build_text_payload(
                to,
                "Sorry, we could not initialize your payment right now. "
                "Please try again later.\n\n"
                "Reply 'menu' to return to the main menu.",
            ),
        )
