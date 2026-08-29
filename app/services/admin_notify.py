import logging
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org"


async def _send_telegram(chat_id: str, text: str) -> dict[str, Any] | None:
    if not settings.TELEGRAM_BOT_TOKEN or not chat_id:
        return None
    url = f"{TELEGRAM_API}/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json={
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "Markdown",
                "disable_web_page_preview": True,
            })
            resp.raise_for_status()
            return resp.json()
    except Exception:
        logger.exception("Failed to send admin Telegram notification")
        return None


async def _send_whatsapp(phone: str, text: str) -> dict[str, Any] | None:
    if not settings.WA_ACCESS_TOKEN or not settings.WA_PHONE_NUMBER_ID or not phone:
        return None
    url = f"https://graph.facebook.com/{settings.WA_API_VERSION}/{settings.WA_PHONE_NUMBER_ID}/messages"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                url,
                headers={"Authorization": f"Bearer {settings.WA_ACCESS_TOKEN}"},
                json={
                    "messaging_product": "whatsapp",
                    "to": phone,
                    "type": "text",
                    "text": {"body": text},
                },
            )
            resp.raise_for_status()
            return resp.json()
    except Exception:
        logger.exception("Failed to send admin WhatsApp notification")
        return None


def _dashboard_link(path: str) -> str:
    base = settings.ADMIN_DASHBOARD_URL.rstrip("/")
    if not base:
        return ""
    return f"{base}/{path.lstrip('/')}"


def _ticket_text(
    ticket_number: str,
    department: str,
    priority: str,
    subject: str,
    user_id: str,
    event: str,
) -> str:
    dashboard_link = _dashboard_link("/tickets")
    lines = [
        f"*{event}*",
        "",
        f"Ticket: `{ticket_number}`",
        f"Department: {department.title()}",
        f"Priority: {priority.title()}",
        f"Subject: {subject[:120]}",
        f"User: {user_id}",
    ]
    if dashboard_link:
        lines.append(f"\n[Open Dashboard]({dashboard_link})")
    return "\n".join(lines)


async def notify_new_ticket(
    ticket_number: str,
    department: str,
    priority: str,
    subject: str,
    user_id: str,
) -> None:
    text = _ticket_text(
        ticket_number, department, priority, subject, user_id,
        event="New Support Ticket",
    )
    if settings.TELEGRAM_ADMIN_CHAT_ID:
        await _send_telegram(settings.TELEGRAM_ADMIN_CHAT_ID, text)
    if settings.WHATSAPP_ADMIN_PHONE:
        await _send_whatsapp(settings.WHATSAPP_ADMIN_PHONE, text)


async def notify_human_agent_request(
    ticket_number: str,
    department: str,
    priority: str,
    subject: str,
    user_id: str,
) -> None:
    text = _ticket_text(
        ticket_number, department, priority, subject, user_id,
        event="Human Agent Requested",
    )
    if settings.TELEGRAM_ADMIN_CHAT_ID:
        await _send_telegram(settings.TELEGRAM_ADMIN_CHAT_ID, text)
    if settings.WHATSAPP_ADMIN_PHONE:
        await _send_whatsapp(settings.WHATSAPP_ADMIN_PHONE, text)


async def notify_escalation(
    ticket_number: str,
    department: str,
    priority: str,
    reason: str,
    user_id: str,
) -> None:
    dashboard_link = _dashboard_link("/tickets")
    lines = [
        "*Ticket Escalated*",
        "",
        f"Ticket: `{ticket_number}`",
        f"Department: {department.title()}",
        f"Priority: {priority.title()}",
        f"Reason: {reason}",
        f"User: {user_id}",
    ]
    if dashboard_link:
        lines.append(f"\n[Open Dashboard]({dashboard_link})")
    text = "\n".join(lines)

    if settings.TELEGRAM_ADMIN_CHAT_ID:
        await _send_telegram(settings.TELEGRAM_ADMIN_CHAT_ID, text)
    if settings.WHATSAPP_ADMIN_PHONE:
        await _send_whatsapp(settings.WHATSAPP_ADMIN_PHONE, text)


async def notify_ticket_assigned(
    ticket_number: str,
    agent_name: str,
    subject: str,
) -> None:
    dashboard_link = _dashboard_link("/tickets")
    lines = [
        "*Ticket Assigned*",
        "",
        f"Ticket: `{ticket_number}`",
        f"Assigned to: {agent_name}",
        f"Subject: {subject[:120]}",
    ]
    if dashboard_link:
        lines.append(f"\n[Open Dashboard]({dashboard_link})")
    text = "\n".join(lines)

    if settings.TELEGRAM_ADMIN_CHAT_ID:
        await _send_telegram(settings.TELEGRAM_ADMIN_CHAT_ID, text)
    if settings.WHATSAPP_ADMIN_PHONE:
        await _send_whatsapp(settings.WHATSAPP_ADMIN_PHONE, text)
