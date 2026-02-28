"""Scrubbing SpanProcessor for video-ai-telemetry.

Scans string-valued span attributes before export and redacts values matching
sensitive patterns (passwords, tokens, secrets, API keys, credit card numbers,
email addresses, phone numbers, etc.).

Usage::

    from video_ai_telemetry.logging.scrubber import ScrubbingSpanProcessor

    processor = ScrubbingSpanProcessor(
        extra_patterns=[r"ssn", r"dob"],
        callback=my_allow_list_fn,
    )
    tracer_provider.add_span_processor(processor)

The optional *callback* receives ``(key, value, pattern)`` and should return
``True`` to skip redaction for that attribute (i.e. allow-list it).
"""

from __future__ import annotations

import re
from collections.abc import Callable

from opentelemetry.sdk.trace import ReadableSpan, SpanProcessor

# ---------------------------------------------------------------------------
# Default sensitive patterns
# ---------------------------------------------------------------------------

DEFAULT_SCRUB_PATTERNS: list[str] = [
    r"password",
    r"token",
    r"secret",
    r"api[_-]?key",
    r"authorization",
    r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b",  # Credit card
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",  # Email
    r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b",  # Phone number
]


# ---------------------------------------------------------------------------
# ScrubbingSpanProcessor
# ---------------------------------------------------------------------------


class ScrubbingSpanProcessor(SpanProcessor):
    """A SpanProcessor that redacts sensitive string-valued span attributes.

    On ``on_end`` the processor iterates over all span attributes and
    replaces the value of any string attribute whose *key* or *value* matches
    a sensitive pattern with the literal string ``"[REDACTED]"``.

    Parameters
    ----------
    extra_patterns:
        Additional regex patterns (as strings) to add to the default set.
        Each pattern is compiled case-insensitively.
    callback:
        Optional callable ``(key: str, value: str, pattern: re.Pattern) -> bool``.
        When provided it is invoked for every attribute that would be redacted.
        Returning ``True`` from the callback skips redaction for that attribute
        (i.e. acts as an allow-list entry).
    """

    def __init__(
        self,
        extra_patterns: list[str] | None = None,
        callback: Callable[[str, str, re.Pattern], bool] | None = None,
    ) -> None:
        patterns = DEFAULT_SCRUB_PATTERNS + (extra_patterns or [])
        self._compiled_patterns: list[re.Pattern] = [re.compile(p, re.IGNORECASE) for p in patterns]
        self._callback = callback

    # ------------------------------------------------------------------
    # SpanProcessor interface
    # ------------------------------------------------------------------

    def on_start(self, span, parent_context=None) -> None:  # noqa: ANN001
        """No-op — scrubbing is applied at export time (on_end)."""

    def on_end(self, span: ReadableSpan) -> None:
        """Redact sensitive attribute values before the span is exported."""
        if not hasattr(span, "_attributes") or span._attributes is None:
            return

        for key, value in list(span._attributes.items()):
            if not isinstance(value, str):
                # Only string-valued attributes are scanned.
                continue

            for pattern in self._compiled_patterns:
                if pattern.search(key) or pattern.search(value):
                    # Give the caller a chance to allow-list this attribute.
                    if self._callback is not None and self._callback(key, value, pattern):
                        continue
                    span._attributes[key] = "[REDACTED]"
                    break

    def shutdown(self) -> None:
        """No-op — nothing to clean up."""

    def force_flush(self, timeout_millis: int | None = None) -> bool:
        """No-op — this processor is synchronous; always returns True."""
        return True
