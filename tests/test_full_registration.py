"""Integration tests for the full registration flow via WhatsApp."""

import json
from unittest.mock import AsyncMock, patch

import pytest

from app.config import settings
from tests.conftest import build_whatsapp_text_payload, sign_whatsapp_payload


@pytest.mark.asyncio
async def test_new_user_receives_greeting_and_menu(async_client):
    payload = build_whatsapp_text_payload(text="Hi")
    body = json.dumps(payload).encode()
    sig = sign_whatsapp_payload(body, settings.WA_APP_SECRET)

    with (
        patch("app.api.v1.whatsapp.process_inbound_message", new_callable=AsyncMock) as mock_process,
        patch("app.services.whatsapp_service.wa_service.mark_as_read", new_callable=AsyncMock),
    ):
        resp = await async_client.post(
            "/api/v1/whatsapp/webhook",
            content=body,
            headers={"X-Hub-Signature-256": sig},
        )

    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
    mock_process.assert_called_once()
    call_kwargs = mock_process.call_args
    assert call_kwargs.kwargs["whatsapp_id"] == "2348012345678"
    assert call_kwargs.kwargs["user_input"] == "Hi"


@pytest.mark.asyncio
async def test_menu_keyword_routed_correctly(async_client):
    payload = build_whatsapp_text_payload(text="menu")
    body = json.dumps(payload).encode()
    sig = sign_whatsapp_payload(body, settings.WA_APP_SECRET)

    with (
        patch("app.api.v1.whatsapp.process_inbound_message", new_callable=AsyncMock) as mock_process,
        patch("app.services.whatsapp_service.wa_service.mark_as_read", new_callable=AsyncMock),
    ):
        resp = await async_client.post(
            "/api/v1/whatsapp/webhook",
            content=body,
            headers={"X-Hub-Signature-256": sig},
        )

    assert resp.status_code == 200
    mock_process.assert_called_once()
    assert mock_process.call_args.kwargs["user_input"] == "menu"


@pytest.mark.asyncio
async def test_webhook_rejects_missing_signature(async_client):
    payload = build_whatsapp_text_payload()
    body = json.dumps(payload).encode()

    resp = await async_client.post(
        "/api/v1/whatsapp/webhook",
        content=body,
        headers={"X-Hub-Signature-256": "sha256=invalid"},
    )

    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_webhook_rejects_no_app_secret(async_client):
    payload = build_whatsapp_text_payload()
    body = json.dumps(payload).encode()

    with patch.object(settings, "WA_APP_SECRET", ""):
        resp = await async_client.post(
            "/api/v1/whatsapp/webhook",
            content=body,
        )

    assert resp.status_code == 500


@pytest.mark.asyncio
async def test_webhook_verification_with_correct_token(async_client):
    resp = await async_client.get(
        "/api/v1/whatsapp/webhook",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": settings.WA_VERIFY_TOKEN,
            "hub.challenge": "CHALLENGE_OK",
        },
    )
    assert resp.status_code == 200
    assert resp.text == "CHALLENGE_OK"


@pytest.mark.asyncio
async def test_webhook_verification_with_wrong_token(async_client):
    resp = await async_client.get(
        "/api/v1/whatsapp/webhook",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "wrong-token",
            "hub.challenge": "CHALLENGE",
        },
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_webhook_processes_multiple_messages(async_client):
    payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "BIZ_ID",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {
                                "display_phone_number": "2348099999999",
                                "phone_number_id": "PHONE_ID",
                            },
                            "contacts": [
                                {"profile": {"name": "User A"}, "wa_id": "23480111"},
                                {"profile": {"name": "User B"}, "wa_id": "23480222"},
                            ],
                            "messages": [
                                {
                                    "from": "23480111",
                                    "id": "msg1",
                                    "timestamp": "1700000001",
                                    "text": {"body": "Hello"},
                                    "type": "text",
                                },
                                {
                                    "from": "23480222",
                                    "id": "msg2",
                                    "timestamp": "1700000002",
                                    "text": {"body": "Help"},
                                    "type": "text",
                                },
                            ],
                        },
                        "field": "messages",
                    }
                ],
            }
        ],
    }
    body = json.dumps(payload).encode()
    sig = sign_whatsapp_payload(body, settings.WA_APP_SECRET)

    with (
        patch("app.api.v1.whatsapp.process_inbound_message", new_callable=AsyncMock) as mock_process,
        patch("app.services.whatsapp_service.wa_service.mark_as_read", new_callable=AsyncMock),
    ):
        resp = await async_client.post(
            "/api/v1/whatsapp/webhook",
            content=body,
            headers={"X-Hub-Signature-256": sig},
        )

    assert resp.status_code == 200
    assert mock_process.call_count == 2
