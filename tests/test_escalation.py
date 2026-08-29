"""Integration tests for the escalation flow — AI fallback + ticket creation."""

import json
from unittest.mock import AsyncMock, patch

import pytest

from app.config import settings
from app.services.conversation_engine import _is_natural_language_query
from tests.conftest import build_whatsapp_text_payload, sign_whatsapp_payload


@pytest.fixture
def async_client():
    from httpx import ASGITransport, AsyncClient
    from app.main import app

    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


def _post_webhook(async_client, text: str):
    payload = build_whatsapp_text_payload(text=text)
    body = json.dumps(payload).encode()
    sig = sign_whatsapp_payload(body, settings.WA_APP_SECRET)
    return async_client.post(
        "/api/v1/whatsapp/webhook",
        content=body,
        headers={"X-Hub-Signature-256": sig},
    )


@pytest.mark.asyncio
async def test_natural_language_detected_for_ai_query(async_client):
    with (
        patch("app.api.v1.whatsapp.process_inbound_message", new_callable=AsyncMock) as mock_process,
        patch("app.services.whatsapp_service.wa_service.mark_as_read", new_callable=AsyncMock),
    ):
        resp = await _post_webhook(async_client, "How much is the AI programme for a 10-year-old?")

    assert resp.status_code == 200
    mock_process.assert_called_once()
    user_input = mock_process.call_args.kwargs["user_input"]
    assert _is_natural_language_query(user_input) is True


@pytest.mark.asyncio
async def test_escalation_keywords_trigger_intent_detection():
    assert _is_natural_language_query("I want a refund for my payment from last month")
    assert _is_natural_language_query("Can I speak to someone about my child's enrollment?")
    assert _is_natural_language_query("I need help with payment issues")


@pytest.mark.asyncio
async def test_short_messages_do_not_trigger_nl():
    assert not _is_natural_language_query("ok")
    assert not _is_natural_language_query("hi")
    assert not _is_natural_language_query("menu_browse_programmes")


@pytest.mark.asyncio
async def test_admin_ticket_list_requires_auth(async_client):
    resp = await async_client.get("/api/v1/admin/tickets")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_admin_inbox_requires_auth(async_client):
    resp = await async_client.get("/api/v1/admin/inbox")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_admin_reply_requires_auth(async_client):
    resp = await async_client.post(
        "/api/v1/admin/reply",
        json={"whatsapp_number": "2348012345678", "message": "Test"},
    )
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_admin_register_requires_super_admin(async_client):
    from unittest.mock import MagicMock
    from app.utils.auth import get_current_user
    from app.main import app

    mock_agent = MagicMock()
    mock_agent.role = "support_agent"
    mock_agent.id = "00000000-0000-0000-0000-000000000001"
    mock_agent.is_active = True

    app.dependency_overrides[get_current_user] = lambda: mock_agent
    try:
        resp = await async_client.post(
            "/api/v1/auth/register",
            json={
                "email": "new@test.com",
                "full_name": "New User",
                "password": "secure123",
                "role": "support_agent",
            },
        )
        assert resp.status_code == 403
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_expired_token_rejected(async_client, expired_token):
    resp = await async_client.get(
        "/api/v1/admin/inbox",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token_rejected_as_access(async_client, refresh_token_as_access):
    resp = await async_client.get(
        "/api/v1/admin/inbox",
        headers={"Authorization": f"Bearer {refresh_token_as_access}"},
    )
    assert resp.status_code == 401
