"""Integration tests for notification/reminder system — preference checks, dedup, error handling."""

from unittest.mock import AsyncMock, MagicMock, patch
import uuid

import pytest

from app.services.notification_service import (
    PREF_MAP,
    check_preference,
    is_duplicate,
)


class TestNotificationPreferenceMap:
    def test_class_reminder_maps_correctly(self):
        assert PREF_MAP["class_reminder_24h"] == "class_reminders"
        assert PREF_MAP["class_reminder_1h"] == "class_reminders"

    def test_payment_reminder_maps_correctly(self):
        assert PREF_MAP["payment_reminder_7day"] == "payment_reminders"
        assert PREF_MAP["payment_reminder_due"] == "payment_reminders"
        assert PREF_MAP["payment_reminder_overdue"] == "payment_reminders"

    def test_marketing_maps_correctly(self):
        assert PREF_MAP["marketing"] == "marketing"

    def test_unknown_type_defaults_to_allowed(self):
        assert "unknown_type" not in PREF_MAP


@pytest.mark.asyncio
async def test_check_preference_allows_unknown_type():
    mock_db = AsyncMock()
    result = await check_preference(uuid.uuid4(), "unknown_type", mock_db)
    assert result is True


@pytest.mark.asyncio
async def test_check_preference_allows_when_no_prefs():
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result

    result = await check_preference(uuid.uuid4(), "class_reminder", mock_db)
    assert result is True


@pytest.mark.asyncio
async def test_is_duplicate_returns_false_for_new():
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result

    result = await is_duplicate("class_reminder", "unique_key_123", mock_db)
    assert result is False


@pytest.mark.asyncio
async def test_is_duplicate_returns_true_for_existing():
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = MagicMock()
    mock_db.execute.return_value = mock_result

    result = await is_duplicate("class_reminder", "existing_key", mock_db)
    assert result is True


class TestEngagementEndpointAuth:
    @pytest.fixture
    def async_client(self):
        from httpx import ASGITransport, AsyncClient
        from app.main import app

        transport = ASGITransport(app=app)
        return AsyncClient(transport=transport, base_url="http://test")

    @pytest.mark.asyncio
    async def test_attendance_requires_auth(self, async_client):
        resp = await async_client.post(
            "/api/v1/attendance",
            json={
                "student_id": str(uuid.uuid4()),
                "date": "2026-08-14",
                "status": "present",
            },
        )
        assert resp.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_progress_notify_requires_auth(self, async_client):
        resp = await async_client.post(
            "/api/v1/progress/notify",
            json={
                "student_id": str(uuid.uuid4()),
                "notification_type": "grade_posted",
                "title": "Math Grade",
                "message": "Your child scored 90%",
            },
        )
        assert resp.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_certificate_notify_requires_auth(self, async_client):
        resp = await async_client.post(
            "/api/v1/certificate/notify",
            json={
                "student_id": str(uuid.uuid4()),
                "programme_name": "AI for Kids",
            },
        )
        assert resp.status_code in (401, 403)


class TestNotificationEndpointAuth:
    @pytest.fixture
    def async_client(self):
        from httpx import ASGITransport, AsyncClient
        from app.main import app

        transport = ASGITransport(app=app)
        return AsyncClient(transport=transport, base_url="http://test")

    @pytest.mark.asyncio
    async def test_list_notifications_requires_auth(self, async_client):
        resp = await async_client.get("/api/v1/notifications/")
        assert resp.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_get_notification_requires_auth(self, async_client):
        resp = await async_client.get(f"/api/v1/notifications/{uuid.uuid4()}")
        assert resp.status_code in (401, 403)
