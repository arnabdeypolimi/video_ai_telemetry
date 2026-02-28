"""AdaptiveSampler — time-window + anomaly-based sampling.

Three-tier decision (evaluated in order):
1. FORCE   -> always_trace=True on the decorator -> always create span
2. ANOMALY -> elapsed_ms > anomaly_threshold_ms -> always create span
3. WINDOW  -> one span per stage per window_s -> rate limit
"""

from __future__ import annotations

import threading
import time


class AdaptiveSampler:
    """Decides whether to create a span for a given pipeline stage."""

    def __init__(
        self,
        window_s: float = 1.0,
        anomaly_threshold_ms: float = 50.0,
    ) -> None:
        self._window_s = window_s
        self._anomaly_threshold_ms = anomaly_threshold_ms
        self._last_span_time: dict[str, float] = {}
        self._lock = threading.Lock()

    def should_sample(
        self,
        stage_name: str,
        *,
        always_trace: bool = False,
        elapsed_ms: float | None = None,
    ) -> bool:
        """Decide whether to create a span.

        Args:
            stage_name: Name of the pipeline stage.
            always_trace: If True, always sample (force tier).
            elapsed_ms: If provided and exceeds threshold, always sample (anomaly tier).

        Returns:
            True if a span should be created.
        """
        if always_trace:
            return True

        if elapsed_ms is not None and elapsed_ms > self._anomaly_threshold_ms:
            return True

        now = time.monotonic()
        with self._lock:
            last = self._last_span_time.get(stage_name, 0.0)
            if now - last >= self._window_s:
                self._last_span_time[stage_name] = now
                return True
        return False
