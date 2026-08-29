from app.flows import FlowResult
from app.utils.whatsapp_helpers import build_interactive_list_payload

MENU_OPTIONS = [
    {
        "id": "menu_browse_programmes",
        "title": "Browse Programmes",
        "description": "View available programmes and schedules",
    },
    {
        "id": "menu_register_student",
        "title": "Register a Student",
        "description": "Enrol your child in a programme",
    },
    {
        "id": "menu_make_payment",
        "title": "Make Payment",
        "description": "Pay school fees, invoices & enrollments",
    },
    {
        "id": "menu_check_balance",
        "title": "Check Balance",
        "description": "View outstanding fees and payment history",
    },
    {
        "id": "menu_my_account",
        "title": "My Account",
        "description": "View your children and class schedules",
    },
    {
        "id": "menu_notifications",
        "title": "Notification Settings",
        "description": "Manage your reminder preferences",
    },
    {
        "id": "menu_academic_calendar",
        "title": "Academic Calendar",
        "description": "View upcoming term dates and school events",
    },
    {
        "id": "menu_get_help",
        "title": "Get Help",
        "description": "Speak with our support team",
    },
    {
        "id": "menu_partnership",
        "title": "School Partnership",
        "description": "Partner your school with Edpassare",
    },
]

FLOW_MAP = {
    "menu_browse_programmes": "enquiry",
    "menu_register_student": "registration",
    "menu_make_payment": "payment",
    "menu_check_balance": "billing",
    "menu_my_account": "my_account",
    "menu_notifications": "notification_prefs",
    "menu_academic_calendar": "calendar",
    "menu_get_help": "support",
    "menu_partnership": "partnership",
}


def build_main_menu(to: str) -> dict:
    return build_interactive_list_payload(
        to=to,
        header="Edpassare",
        body=(
            "Welcome to Edpassare! How can we help you today?\n\n"
            "Please select an option below."
        ),
        button_text="View Options",
        rows=MENU_OPTIONS,
        footer="Reply anytime with 'menu' to return here.",
        section_title="Main Menu",
    )


async def handle_menu_selection(
    user_input: str,
    flow_data: dict,
) -> FlowResult:
    selected_flow = FLOW_MAP.get(user_input)

    if selected_flow:
        return FlowResult(
            next_flow=selected_flow,
            next_step="start",
            flow_data=flow_data,
        )

    return FlowResult(
        flow_data=flow_data,
        next_flow="main_menu",
        next_step="show",
    )
