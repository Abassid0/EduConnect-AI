from typing import Any


def build_text_payload(to: str, body: str) -> dict[str, Any]:
    return {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": "text",
        "text": {"preview_url": False, "body": body},
    }


def build_interactive_button_payload(
    to: str,
    body: str,
    buttons: list[dict[str, str]],
    header: str | None = None,
    footer: str | None = None,
) -> dict[str, Any]:
    action_buttons = [
        {"type": "reply", "reply": {"id": b["id"], "title": b["title"]}}
        for b in buttons[:3]
    ]
    interactive: dict[str, Any] = {
        "type": "button",
        "body": {"text": body},
        "action": {"buttons": action_buttons},
    }
    if header:
        interactive["header"] = {"type": "text", "text": header}
    if footer:
        interactive["footer"] = {"text": footer}
    return {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": "interactive",
        "interactive": interactive,
    }


def build_interactive_list_payload(
    to: str,
    body: str,
    button_text: str,
    rows: list[dict[str, str]],
    header: str | None = None,
    footer: str | None = None,
    section_title: str = "Options",
) -> dict[str, Any]:
    truncated_rows = [
        {
            "id": r["id"],
            "title": r["title"][:24],
            "description": r.get("description", "")[:72],
        }
        for r in rows[:10]
    ]
    interactive: dict[str, Any] = {
        "type": "list",
        "body": {"text": body},
        "action": {
            "button": button_text[:20],
            "sections": [{"title": section_title, "rows": truncated_rows}],
        },
    }
    if header:
        interactive["header"] = {"type": "text", "text": header}
    if footer:
        interactive["footer"] = {"text": footer}
    return {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": "interactive",
        "interactive": interactive,
    }


def build_template_payload(
    to: str,
    template_name: str,
    language_code: str = "en",
    params: list[str] | None = None,
) -> dict[str, Any]:
    components: list[dict[str, Any]] = []
    if params:
        components.append(
            {
                "type": "body",
                "parameters": [
                    {"type": "text", "text": p} for p in params
                ],
            }
        )
    return {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "template",
        "template": {
            "name": template_name,
            "language": {"code": language_code},
            "components": components,
        },
    }
