"""Channel-aware messaging abstraction.

All flows build WhatsApp-format payloads. This module routes those payloads
to the correct transport: WhatsApp Cloud API for production, Telegram Bot
API for free testing and prototyping.
"""

import logging
from typing import Any, Protocol

logger = logging.getLogger(__name__)

CHANNEL_WHATSAPP = "whatsapp"
CHANNEL_TELEGRAM = "telegram"


class MessagingTransport(Protocol):
    async def _send(self, payload: dict[str, Any]) -> dict[str, Any]: ...


async def send_payload(
    channel: str,
    chat_id: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Send a WhatsApp-format payload via the appropriate channel transport."""
    if channel == CHANNEL_TELEGRAM:
        from app.services.telegram_service import telegram_service
        return await telegram_service.send_wa_payload(chat_id, payload)

    from app.services.whatsapp_service import wa_service
    return await wa_service._send(payload)


async def send_text(channel: str, chat_id: str, body: str) -> dict[str, Any]:
    if channel == CHANNEL_TELEGRAM:
        from app.services.telegram_service import telegram_service
        return await telegram_service.send_text(chat_id, body)

    from app.services.whatsapp_service import wa_service
    return await wa_service.send_text(chat_id, body)


async def mark_as_read(channel: str, message_id: str) -> dict[str, Any] | None:
    if channel == CHANNEL_TELEGRAM:
        return None
    from app.services.whatsapp_service import wa_service
    return await wa_service.mark_as_read(message_id)
