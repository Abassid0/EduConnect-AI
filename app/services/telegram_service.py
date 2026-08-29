import logging
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org"


class TelegramService:
    def __init__(self) -> None:
        self._token = settings.TELEGRAM_BOT_TOKEN

    @property
    def _base_url(self) -> str:
        return f"{TELEGRAM_API}/bot{self._token}"

    async def _call(self, method: str, payload: dict[str, Any]) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self._base_url}/{method}",
                json=payload,
            )
            if response.status_code != 200:
                logger.error(
                    "Telegram API error %s on %s: %s",
                    response.status_code,
                    method,
                    response.text,
                )
            response.raise_for_status()
            return response.json()

    async def send_text(self, chat_id: str, text: str) -> dict[str, Any]:
        return await self._call("sendMessage", {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown",
        })

    async def send_inline_keyboard(
        self,
        chat_id: str,
        text: str,
        buttons: list[list[dict[str, str]]],
    ) -> dict[str, Any]:
        return await self._call("sendMessage", {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown",
            "reply_markup": {"inline_keyboard": buttons},
        })

    async def answer_callback_query(
        self, callback_query_id: str, text: str | None = None
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"callback_query_id": callback_query_id}
        if text:
            payload["text"] = text
        return await self._call("answerCallbackQuery", payload)

    async def send_wa_payload(self, chat_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Translate a WhatsApp-format payload and send it via Telegram."""
        msg_type = payload.get("type", "text")

        if msg_type == "text":
            body = payload.get("text", {}).get("body", "")
            return await self.send_text(chat_id, body)

        if msg_type == "interactive":
            return await self._send_interactive(chat_id, payload)

        if msg_type == "template":
            return await self._send_template(chat_id, payload)

        body = payload.get("text", {}).get("body", str(payload))
        return await self.send_text(chat_id, body)

    async def _send_interactive(
        self, chat_id: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        interactive = payload.get("interactive", {})
        interactive_type = interactive.get("type")

        header = interactive.get("header", {}).get("text", "")
        body = interactive.get("body", {}).get("text", "")
        footer = interactive.get("footer", {}).get("text", "")

        text_parts = []
        if header:
            text_parts.append(f"*{header}*")
        if body:
            text_parts.append(body)
        if footer:
            text_parts.append(f"_{footer}_")
        text = "\n\n".join(text_parts) or "Choose an option:"

        if interactive_type == "button":
            buttons_data = interactive.get("action", {}).get("buttons", [])
            keyboard = [
                [{"text": b["reply"]["title"], "callback_data": b["reply"]["id"]}]
                for b in buttons_data
            ]
            return await self.send_inline_keyboard(chat_id, text, keyboard)

        if interactive_type == "list":
            sections = interactive.get("action", {}).get("sections", [])
            keyboard = []
            for section in sections:
                for row in section.get("rows", []):
                    label = row["title"]
                    desc = row.get("description", "")
                    display = f"{label} — {desc}" if desc else label
                    keyboard.append([{
                        "text": display[:64],
                        "callback_data": row["id"][:64],
                    }])
            return await self.send_inline_keyboard(chat_id, text, keyboard)

        return await self.send_text(chat_id, text)

    async def _send_template(
        self, chat_id: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        from app.services.template_registry import render

        template = payload.get("template", {})
        name = template.get("name", "unknown_template")
        components = template.get("components", [])

        params = []
        for comp in components:
            if comp.get("type") == "body":
                for p in comp.get("parameters", []):
                    params.append(p.get("text", ""))

        text = render(name, params or None)
        return await self.send_text(chat_id, text)

    async def set_webhook(self, url: str) -> dict[str, Any]:
        payload: dict[str, Any] = {"url": url}
        if settings.TELEGRAM_WEBHOOK_SECRET:
            payload["secret_token"] = settings.TELEGRAM_WEBHOOK_SECRET
        return await self._call("setWebhook", payload)

    async def delete_webhook(self) -> dict[str, Any]:
        return await self._call("deleteWebhook", {})

    async def get_me(self) -> dict[str, Any]:
        return await self._call("getMe", {})


telegram_service = TelegramService()
