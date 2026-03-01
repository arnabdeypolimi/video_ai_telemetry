"""Tests for ScrubbingSpanProcessor (logging/scrubber.py).

Validates:
1. Default patterns redact password, email, credit card, and phone number.
2. Custom extra_patterns are applied in addition to the defaults.
3. A callback can allow-list specific attributes (skip redaction).
4. Non-string attributes are not touched.
5. Attributes without sensitive content are preserved as-is.
"""

from __future__ import annotations

import re
from unittest.mock import MagicMock

import pytest

from modaltrace.logging.scrubber import ScrubbingSpanProcessor

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_span(attributes: dict) -> MagicMock:
    """Return a mock ReadableSpan with the given _attributes dict."""
    span = MagicMock()
    span._attributes = dict(attributes)
    return span


def _run_processor(attributes: dict, **kwargs) -> dict:
    """Create a processor with kwargs, run on_end, and return the final attributes."""
    processor = ScrubbingSpanProcessor(**kwargs)
    span = _make_span(attributes)
    processor.on_end(span)
    return span._attributes


# ---------------------------------------------------------------------------
# 1. Default patterns
# ---------------------------------------------------------------------------


class TestDefaultPatterns:
    def test_password_key_is_redacted(self):
        result = _run_processor({"password": "s3cr3t!"})
        assert result["password"] == "[REDACTED]"

    def test_password_in_compound_key_is_redacted(self):
        result = _run_processor({"user_password": "hunter2"})
        assert result["user_password"] == "[REDACTED]"

    def test_token_key_is_redacted(self):
        result = _run_processor({"auth_token": "eyJhbGci..."})
        assert result["auth_token"] == "[REDACTED]"

    def test_secret_key_is_redacted(self):
        result = _run_processor({"client_secret": "abc123"})
        assert result["client_secret"] == "[REDACTED]"

    def test_api_key_key_is_redacted(self):
        result = _run_processor({"api_key": "sk-abcdef"})
        assert result["api_key"] == "[REDACTED]"

    def test_apikey_without_separator_is_redacted(self):
        result = _run_processor({"apikey": "sk-abcdef"})
        assert result["apikey"] == "[REDACTED]"

    def test_authorization_key_is_redacted(self):
        result = _run_processor({"authorization": "Bearer some-token"})
        assert result["authorization"] == "[REDACTED]"

    def test_email_value_is_redacted(self):
        result = _run_processor({"user_contact": "alice@example.com"})
        assert result["user_contact"] == "[REDACTED]"

    def test_credit_card_value_is_redacted(self):
        result = _run_processor({"card_info": "4111 1111 1111 1111"})
        assert result["card_info"] == "[REDACTED]"

    def test_credit_card_with_dashes_is_redacted(self):
        result = _run_processor({"payment": "4111-1111-1111-1111"})
        assert result["payment"] == "[REDACTED]"

    def test_phone_number_value_is_redacted(self):
        result = _run_processor({"phone": "555-867-5309"})
        assert result["phone"] == "[REDACTED]"

    def test_phone_with_dots_is_redacted(self):
        result = _run_processor({"contact": "555.867.5309"})
        assert result["contact"] == "[REDACTED]"

    def test_sensitive_word_in_value_triggers_redaction(self):
        """A value containing the word 'password' should also be redacted."""
        result = _run_processor({"hint": "your password is here"})
        assert result["hint"] == "[REDACTED]"


# ---------------------------------------------------------------------------
# 2. Custom extra patterns
# ---------------------------------------------------------------------------


class TestExtraPatterns:
    def test_extra_pattern_redacts_matching_key(self):
        result = _run_processor({"ssn": "123-45-6789"}, extra_patterns=[r"ssn"])
        assert result["ssn"] == "[REDACTED]"

    def test_extra_pattern_redacts_matching_value(self):
        result = _run_processor(
            {"identifier": "dob:1990-01-01"},
            extra_patterns=[r"dob"],
        )
        assert result["identifier"] == "[REDACTED]"

    def test_extra_pattern_does_not_affect_unrelated_attributes(self):
        result = _run_processor(
            {"frame_count": "42"},
            extra_patterns=[r"ssn"],
        )
        assert result["frame_count"] == "42"

    def test_extra_pattern_combined_with_default(self):
        """Both the default and extra patterns should be active simultaneously."""
        result = _run_processor(
            {"password": "hunter2", "dob": "1990-01-01"},
            extra_patterns=[r"dob"],
        )
        assert result["password"] == "[REDACTED]"
        assert result["dob"] == "[REDACTED]"

    def test_extra_pattern_is_case_insensitive(self):
        result = _run_processor({"SSN": "123-45-6789"}, extra_patterns=[r"ssn"])
        assert result["SSN"] == "[REDACTED]"


# ---------------------------------------------------------------------------
# 3. Callback allow-list
# ---------------------------------------------------------------------------


class TestCallbackAllowList:
    def test_callback_returning_true_skips_redaction(self):
        """A callback that returns True should prevent the attribute from being redacted."""

        def allow_all(key, value, pattern):
            return True  # Allow everything

        result = _run_processor({"password": "s3cr3t!"}, callback=allow_all)
        assert result["password"] == "s3cr3t!"

    def test_callback_returning_false_allows_redaction(self):
        """A callback that returns False should let redaction proceed normally."""

        def deny_all(key, value, pattern):
            return False  # Block nothing — allow redaction to proceed

        result = _run_processor({"password": "s3cr3t!"}, callback=deny_all)
        assert result["password"] == "[REDACTED]"

    def test_callback_can_selectively_allow(self):
        """Callback can allow-list specific keys while letting others be redacted."""

        def allow_known_safe(key, value, pattern):
            return key == "safe_token"  # Allow only this one

        result = _run_processor(
            {"safe_token": "public-value", "secret": "private"},
            callback=allow_known_safe,
        )
        assert result["safe_token"] == "public-value"
        assert result["secret"] == "[REDACTED]"

    def test_callback_receives_correct_arguments(self):
        """Callback must be called with (key, value, compiled_pattern)."""
        received_calls: list[tuple] = []

        def capturing_callback(key, value, pattern):
            received_calls.append((key, value, pattern))
            return False  # Allow redaction

        _run_processor({"password": "secret123"}, callback=capturing_callback)

        assert len(received_calls) == 1
        key, value, pattern = received_calls[0]
        assert key == "password"
        assert value == "secret123"
        assert isinstance(pattern, re.Pattern)

    def test_no_callback_does_not_crash(self):
        """When callback=None redaction proceeds without errors."""
        result = _run_processor({"token": "abc"})
        assert result["token"] == "[REDACTED]"


# ---------------------------------------------------------------------------
# 4. Non-string attributes are not touched
# ---------------------------------------------------------------------------


class TestNonStringAttributes:
    def test_integer_attribute_not_touched(self):
        result = _run_processor({"frame_count": 100})
        assert result["frame_count"] == 100

    def test_float_attribute_not_touched(self):
        result = _run_processor({"duration_ms": 47.3})
        assert result["duration_ms"] == pytest.approx(47.3)

    def test_boolean_attribute_not_touched(self):
        result = _run_processor({"is_keyframe": True})
        assert result["is_keyframe"] is True

    def test_none_attribute_not_touched(self):
        result = _run_processor({"optional": None})
        assert result["optional"] is None

    def test_mixed_types_only_string_affected(self):
        """Only the string attribute matching a pattern should be redacted."""
        result = _run_processor({"frame_count": 42, "password": "secret", "drift_ms": 3.14})
        assert result["frame_count"] == 42
        assert result["password"] == "[REDACTED]"
        assert result["drift_ms"] == pytest.approx(3.14)


# ---------------------------------------------------------------------------
# 5. Non-sensitive attributes are preserved
# ---------------------------------------------------------------------------


class TestNonSensitiveAttributesPreserved:
    def test_safe_string_attribute_preserved(self):
        result = _run_processor({"stage_name": "render"})
        assert result["stage_name"] == "render"

    def test_safe_numeric_string_preserved(self):
        result = _run_processor({"frame_id": "1234"})
        assert result["frame_id"] == "1234"

    def test_safe_url_preserved(self):
        result = _run_processor({"endpoint": "https://api.example.com/v1/health"})
        assert result["endpoint"] == "https://api.example.com/v1/health"

    def test_multiple_safe_attributes_all_preserved(self):
        attrs = {
            "pipeline_id": "pipe-001",
            "stage_name": "encode",
            "resolution": "1920x1080",
            "target_fps": "30",
        }
        result = _run_processor(attrs)
        for key, value in attrs.items():
            assert result[key] == value

    def test_empty_attributes_dict_no_error(self):
        result = _run_processor({})
        assert result == {}


# ---------------------------------------------------------------------------
# 6. Edge cases: span without _attributes
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_span_without_attributes_attr_does_not_crash(self):
        """on_end should be a no-op when the span has no _attributes attribute."""
        processor = ScrubbingSpanProcessor()
        span = MagicMock(spec=[])  # spec=[] means no attributes at all
        processor.on_end(span)  # Should not raise

    def test_span_with_none_attributes_does_not_crash(self):
        """on_end should be a no-op when _attributes is None."""
        processor = ScrubbingSpanProcessor()
        span = MagicMock()
        span._attributes = None
        processor.on_end(span)  # Should not raise

    def test_shutdown_does_not_raise(self):
        processor = ScrubbingSpanProcessor()
        processor.shutdown()  # Should not raise

    def test_force_flush_returns_true(self):
        processor = ScrubbingSpanProcessor()
        assert processor.force_flush() is True
        assert processor.force_flush(timeout_millis=1000) is True

    def test_on_start_does_not_raise(self):
        processor = ScrubbingSpanProcessor()
        span = MagicMock()
        processor.on_start(span)  # Should not raise
        processor.on_start(span, parent_context=MagicMock())  # Should not raise
