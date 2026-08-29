"""Integration tests for AI assistant service — rate limiting, intent detection, confidence scoring."""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.ai_service import (
    _check_rate_limit,
    _contains_escalation_intent,
    _estimate_confidence,
    _rate_limits,
    _tool_get_support_departments,
    AI_RATE_LIMIT,
)
from app.services.conversation_engine import _is_natural_language_query


class TestIntentDetection:
    def test_question_mark_detected(self):
        assert _is_natural_language_query("How much is the fee?")

    def test_keyword_detected(self):
        assert _is_natural_language_query("I want to register my child")

    def test_multi_word_detected(self):
        assert _is_natural_language_query("Tell me about the programmes")

    def test_short_message_ignored(self):
        assert not _is_natural_language_query("ok")

    def test_single_word_ignored(self):
        assert not _is_natural_language_query("hi")

    def test_menu_id_ignored(self):
        assert not _is_natural_language_query("menu_browse_programmes")

    def test_payment_keyword(self):
        assert _is_natural_language_query("payment status for my child")

    def test_agent_request(self):
        assert _is_natural_language_query("I want to speak to someone")

    def test_three_word_message(self):
        assert _is_natural_language_query("help me please")

    def test_empty_string(self):
        assert not _is_natural_language_query("")


class TestConfidenceScoring:
    def _mock_response(self, stop_reason="end_turn"):
        r = MagicMock()
        r.stop_reason = stop_reason
        return r

    def test_base_confidence(self):
        score = _estimate_confidence(
            "Here are our programmes.",
            [],
            self._mock_response(),
        )
        assert 0.7 <= score <= 0.8

    def test_tools_boost_confidence(self):
        tools = [{"name": "get_programmes", "input": {}, "output": '[{"name":"AI"}]'}]
        score = _estimate_confidence(
            "We have the AI programme for ages 8-12.",
            tools,
            self._mock_response(),
        )
        assert score > 0.8

    def test_error_tool_lowers_confidence(self):
        tools = [{"name": "get_programmes", "input": {}, "output": '{"error":"not found"}'}]
        score = _estimate_confidence(
            "I couldn't find that programme.",
            tools,
            self._mock_response(),
        )
        assert score < 0.7

    def test_uncertainty_phrases_lower_confidence(self):
        score = _estimate_confidence(
            "I'm not sure about that, let me check.",
            [],
            self._mock_response(),
        )
        assert score <= 0.5

    def test_escalation_language_lowers_confidence(self):
        score = _estimate_confidence(
            "Let me connect you with a staff member.",
            [],
            self._mock_response(),
        )
        assert score < 0.6


class TestEscalationIntent:
    def test_staff_member_detected(self):
        assert _contains_escalation_intent(
            "Let me connect you with a staff member for help."
        )

    def test_team_member_detected(self):
        assert _contains_escalation_intent(
            "I'll connect you to a team member right away."
        )

    def test_normal_response_not_flagged(self):
        assert not _contains_escalation_intent(
            "Our AI programme costs NGN 50,000 per term."
        )


class TestRateLimiting:
    def setup_method(self):
        _rate_limits.clear()

    def test_allows_under_limit(self):
        assert _check_rate_limit("conv-1") is True

    def test_blocks_at_limit(self):
        for _ in range(AI_RATE_LIMIT):
            _check_rate_limit("conv-2")
        assert _check_rate_limit("conv-2") is False

    def test_separate_conversations(self):
        for _ in range(AI_RATE_LIMIT):
            _check_rate_limit("conv-3")
        assert _check_rate_limit("conv-4") is True


class TestSupportDepartments:
    def test_returns_all_departments(self):
        depts = _tool_get_support_departments()
        assert len(depts) >= 5
        dept_ids = [d["id"] for d in depts]
        assert "admissions" in dept_ids
        assert "payments" in dept_ids
        assert "general" in dept_ids
