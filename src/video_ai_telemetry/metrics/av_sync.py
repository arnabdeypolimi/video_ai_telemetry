"""AVSyncTracker — audio-video sync drift and jitter measurement.

Cross-stage measurement: audio_captured(chunk_id) records the capture timestamp,
frame_rendered(chunk_id) computes drift. Positive drift = video lags audio.

Jitter is computed as Mean Absolute Deviation of a rolling window of drift values.
"""

from __future__ import annotations

import threading
import time
from collections import deque

from video_ai_telemetry.conventions.attributes import AVSyncAttributes
from video_ai_telemetry.metrics.instruments import MetricInstruments


class AVSyncTracker:
    """Tracks audio-video synchronization drift and jitter."""

    def __init__(
        self,
        instruments: MetricInstruments,
        drift_warning_ms: float = 40.0,
        chunk_ttl_s: float = 5.0,
        jitter_window: int = 30,
        warning_callback: callable | None = None,
    ) -> None:
        self._instruments = instruments
        self._drift_warning_ms = drift_warning_ms
        self._chunk_ttl_s = chunk_ttl_s
        self._jitter_window = jitter_window
        self._warning_callback = warning_callback

        self._pending: dict[int, tuple[int, int]] = {}  # {chunk_id: (capture_ns, expiry_ns)}
        self._lock = threading.Lock()
        self._drift_window: deque[float] = deque(maxlen=jitter_window)
        self._last_drift_ms: float = 0.0

    @property
    def current_drift_ms(self) -> float:
        return self._last_drift_ms

    @property
    def current_jitter_ms(self) -> float:
        if len(self._drift_window) < 2:
            return 0.0
        values = list(self._drift_window)
        mean = sum(values) / len(values)
        return sum(abs(v - mean) for v in values) / len(values)

    def audio_captured(self, chunk_id: int) -> None:
        """Record the timestamp when an audio chunk was captured."""
        now_ns = time.time_ns()
        expiry_ns = now_ns + int(self._chunk_ttl_s * 1e9)
        with self._lock:
            self._pending[chunk_id] = (now_ns, expiry_ns)

    def frame_rendered(self, chunk_id: int) -> float | None:
        """Record the timestamp when the frame for a chunk was rendered.

        Returns the drift in milliseconds, or None if no matching audio chunk.
        """
        now_ns = time.time_ns()
        with self._lock:
            entry = self._pending.pop(chunk_id, None)

        if entry is None:
            return None

        capture_ns, _ = entry
        drift_ms = (now_ns - capture_ns) / 1e6
        self._last_drift_ms = drift_ms
        self._drift_window.append(drift_ms)

        # Record metrics
        self._instruments.av_sync_drift.record(drift_ms)
        jitter = self.current_jitter_ms
        self._instruments.av_sync_jitter.record(jitter)

        # Warning on excessive drift
        if abs(drift_ms) > self._drift_warning_ms and self._warning_callback:
            self._warning_callback(
                f"A/V drift exceeded threshold: {drift_ms:.1f}ms",
                **{
                    AVSyncAttributes.DRIFT_MS: drift_ms,
                    AVSyncAttributes.CHUNK_ID: chunk_id,
                    AVSyncAttributes.THRESHOLD_MS: self._drift_warning_ms,
                },
            )

        return drift_ms

    def cleanup_expired(self) -> int:
        """Remove expired pending chunks. Returns number of chunks cleaned up."""
        now_ns = time.time_ns()
        expired_count = 0
        with self._lock:
            expired = [cid for cid, (_, expiry_ns) in self._pending.items() if now_ns > expiry_ns]
            for cid in expired:
                del self._pending[cid]
                expired_count += 1

        if expired_count > 0:
            self._instruments.av_sync_unmatched.add(expired_count)

        return expired_count
