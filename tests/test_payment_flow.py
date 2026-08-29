"""Integration tests for payment webhooks and verification endpoints."""

import hashlib
import hmac
import json
from unittest.mock import AsyncMock, patch

import pytest

from app.config import settings
from tests.conftest import sign_paystack_payload


@pytest.fixture
def async_client():
    from httpx import ASGITransport, AsyncClient
    from app.main import app

    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.mark.asyncio
async def test_paystack_webhook_rejects_invalid_signature(async_client):
    payload = {
        "event": "charge.success",
        "data": {"reference": "EDP-PAY-TEST-001", "id": 12345},
    }
    body = json.dumps(payload).encode()

    resp = await async_client.post(
        "/api/v1/payments/webhook/paystack",
        content=body,
        headers={
            "x-paystack-signature": "invalid-signature",
            "Content-Type": "application/json",
        },
    )

    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_paystack_webhook_rejects_empty_signature(async_client):
    payload = {
        "event": "charge.success",
        "data": {"reference": "EDP-PAY-TEST-002"},
    }
    body = json.dumps(payload).encode()

    resp = await async_client.post(
        "/api/v1/payments/webhook/paystack",
        content=body,
        headers={"Content-Type": "application/json"},
    )

    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_paystack_webhook_accepts_valid_signature(async_client):
    payload = {
        "event": "charge.success",
        "data": {"reference": "EDP-PAY-NONEXIST", "id": 99999, "channel": "card"},
    }
    body = json.dumps(payload).encode()
    sig = sign_paystack_payload(body, settings.PAYSTACK_SECRET_KEY)

    with patch(
        "app.services.payment_service.process_webhook_event",
        new_callable=AsyncMock,
        return_value=None,
    ):
        resp = await async_client.post(
            "/api/v1/payments/webhook/paystack",
            content=body,
            headers={
                "x-paystack-signature": sig,
                "Content-Type": "application/json",
            },
        )

    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_payment_list_requires_auth(async_client):
    resp = await async_client.get("/api/v1/payments/")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_payment_verify_requires_auth(async_client):
    resp = await async_client.get("/api/v1/payments/verify/EDP-PAY-TEST-001")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_paystack_webhook_ignores_non_charge_events(async_client):
    payload = {
        "event": "transfer.success",
        "data": {"reference": "TRF-001"},
    }
    body = json.dumps(payload).encode()
    sig = sign_paystack_payload(body, settings.PAYSTACK_SECRET_KEY)

    resp = await async_client.post(
        "/api/v1/payments/webhook/paystack",
        content=body,
        headers={
            "x-paystack-signature": sig,
            "Content-Type": "application/json",
        },
    )

    assert resp.status_code == 200
