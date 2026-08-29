import logging
from typing import Any

import httpx

from app.config import settings
from app.utils.whatsapp_helpers import (
    build_interactive_button_payload,
    build_interactive_list_payload,
    build_template_payload,
    build_text_payload,
)

logger = logging.getLogger(__name__)


class WhatsAppService:
    def __init__(self) -> None:
        self._base_url = settings.wa_api_base
        self._headers = {
            "Authorization": f"Bearer {settings.WA_ACCESS_TOKEN}",
            "Content-Type": "application/json",
        }

    async def _send(self, payload: dict[str, Any]) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self._base_url}/messages",
                headers=self._headers,
                json=payload,
            )
            if response.status_code != 200:
                logger.error(
                    "WhatsApp API error %s: %s",
                    response.status_code,
                    response.text,
                )
            response.raise_for_status()
            return response.json()

    async def send_text(self, to: str, body: str) -> dict[str, Any]:
        payload = build_text_payload(to, body)
        return await self._send(payload)

    async def send_interactive_buttons(
        self,
        to: str,
        body: str,
        buttons: list[dict[str, str]],
        header: str | None = None,
        footer: str | None = None,
    ) -> dict[str, Any]:
        payload = build_interactive_button_payload(to, body, buttons, header, footer)
        return await self._send(payload)

    async def send_interactive_list(
        self,
        to: str,
        body: str,
        button_text: str,
        rows: list[dict[str, str]],
        header: str | None = None,
        footer: str | None = None,
        section_title: str = "Options",
    ) -> dict[str, Any]:
        payload = build_interactive_list_payload(
            to, body, button_text, rows, header, footer, section_title
        )
        return await self._send(payload)

    async def send_template(
        self,
        to: str,
        template_name: str,
        language_code: str = "en",
        params: list[str] | None = None,
    ) -> dict[str, Any]:
        payload = build_template_payload(to, template_name, language_code, params)
        return await self._send(payload)

    async def mark_as_read(self, message_id: str) -> dict[str, Any]:
        payload = {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": message_id,
        }
        return await self._send(payload)


wa_service = WhatsAppService()
