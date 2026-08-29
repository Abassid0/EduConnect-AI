"""
Template registry — single source of truth for all WhatsApp message templates.

Each entry maps a template name to its body string using {{N}} placeholders
(1-indexed, matching Meta's convention).  The render() function substitutes
params so Telegram tests produce the same text parents will see on WhatsApp.
"""

import re

TEMPLATES: dict[str, str] = {

    # ----------------------------------------------------------------
    # Class reminders
    # ----------------------------------------------------------------

    "class_reminder_24h": (
        "Hi {{1}},\n\n"
        "Reminder: {{2}} has a {{3}} class tomorrow at {{4}}.\n\n"
        "See you there!\n\n"
        "— EduConnect AI"
    ),

    "class_reminder_1h": (
        "Hi {{1}},\n\n"
        "{{2}}'s {{3}} class starts in 1 hour ({{4}}).\n\n"
        "Please ensure they are ready. See you soon!\n\n"
        "— EduConnect AI"
    ),

    # ----------------------------------------------------------------
    # Enrollment payment reminders
    # ----------------------------------------------------------------

    "payment_reminder_7day": (
        "Hi {{1}},\n\n"
        "Just a friendly reminder that payment for {{2}}'s enrollment "
        "in {{3}} is due in 7 days.\n\n"
        "Amount: {{4}}\n\n"
        "Reply 'menu' to make a payment.\n\n"
        "— EduConnect AI"
    ),

    "payment_reminder_due": (
        "Hi {{1}},\n\n"
        "Payment for {{2}}'s enrollment in {{3}} is due today.\n\n"
        "Amount: {{4}}\n\n"
        "Please make your payment to secure the spot. "
        "Reply 'menu' and select 'Make Payment'.\n\n"
        "— EduConnect AI"
    ),

    "payment_reminder_overdue": (
        "Hi {{1}},\n\n"
        "Payment for {{2}}'s enrollment in {{3}} is now overdue.\n\n"
        "Amount: {{4}}\n\n"
        "Please pay as soon as possible to avoid losing the enrollment. "
        "Reply 'menu' and select 'Make Payment'.\n\n"
        "— EduConnect AI"
    ),

    # ----------------------------------------------------------------
    # Invoice billing templates  (NEW — Phase 6)
    # ----------------------------------------------------------------

    "invoice_notification": (
        "New Invoice from EduConnect AI\n\n"
        "Invoice #: {{1}}\n"
        "Description: {{2}}\n"
        "Amount Due: {{3}}\n"
        "Due Date: {{4}}\n\n"
        "Reply 'menu' and select 'Make Payment' to pay now, "
        "or 'Check Balance' to view all outstanding fees.\n\n"
        "— EduConnect AI"
    ),

    "invoice_reminder": (
        "Hi {{1}},\n\n"
        "Payment reminder for your invoice:\n\n"
        "Description: {{2}}\n"
        "Amount Due: {{3}}\n"
        "Due Date: {{4}}\n\n"
        "Reply 'menu' and select 'Make Payment' to settle this now.\n\n"
        "— EduConnect AI"
    ),

    # ----------------------------------------------------------------
    # Recommended / future templates
    # ----------------------------------------------------------------

    "attendance_notification": (
        "Attendance update for {{1}}\n\n"
        "Date: {{2}}\n"
        "Status: {{3}}\n"
        "Programme: {{4}}\n\n"
        "Reply 'menu' for more options.\n\n"
        "— EduConnect AI"
    ),

    "progress_update": (
        "{{1}}\n\n"
        "{{2}}\n\n"
        "Student: {{3}}\n\n"
        "Reply 'menu' for more options.\n\n"
        "— EduConnect AI"
    ),

    "certificate_completion": (
        "Congratulations! {{1}} has completed the {{2}} programme!\n\n"
        "A certificate of completion is now available.\n\n"
        "— EduConnect AI"
    ),
}


def render(template_name: str, params: list[str] | None = None) -> str:
    """
    Render a template by substituting {{1}}, {{2}}... with params.

    Returns the rendered text, or a fallback if the template is unknown.
    Handles missing params gracefully — unmatched placeholders are left as-is.
    """
    body = TEMPLATES.get(template_name)
    if body is None:
        params_str = " | ".join(params) if params else ""
        return f"[{template_name}]{': ' + params_str if params_str else ''}"

    if not params:
        return body

    result = body
    for i, value in enumerate(params, start=1):
        result = result.replace(f"{{{{{i}}}}}", value)

    return result


def get_template_body(template_name: str) -> str | None:
    """Return raw template body with placeholders, or None if not found."""
    return TEMPLATES.get(template_name)


def list_templates() -> list[dict]:
    """Return all registered templates as a list for API/docs use."""
    entries = []
    for name, body in TEMPLATES.items():
        param_count = len(set(re.findall(r"\{\{(\d+)\}\}", body)))
        entries.append({
            "name": name,
            "param_count": param_count,
            "preview": body[:80] + ("..." if len(body) > 80 else ""),
        })
    return entries
