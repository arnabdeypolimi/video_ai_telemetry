"""FrameMetricsAggregator — ring buffer + flush thread.

Solves the 30fps overhead problem: OTel calls never happen on the hot path.
Hot path writes to a lock-protected C array (~200ns). A background daemon thread
flushes aggregated samples to OTel histograms at a configurable interval.
"""

from __future__ import annotations

import array
import logging
import threading
from dataclasses import dataclass, field

from modaltrace.conventions.namespaces import NAMESPACE as _NS
from modaltrace.metrics.instruments import MetricInstruments

logger = logging.getLogger(f"{_NS}.aggregator")


@dataclass
class _RingBuffer:
    """Fixed-size ring buffer backed by array.array('d')."""

    capacity: int
    _buf: array.array = field(init=False)
    _write_idx: int = field(init=False, default=0)
    _count: int = field(init=False, default=0)

    def __post_init__(self) -> None:
        self._buf = array.array("d", [0.0] * self.capacity)

    def write(self, value: float) -> None:
        idx = self._write_idx & (self.capacity - 1)
        self._buf[idx] = value
        self._write_idx += 1
        if self._count < self.capacity:
            self._count += 1

    def drain(self) -> list[float]:
        """Return all samples and reset the buffer."""
        if self._count == 0:
            return []
        if self._count < self.capacity:
            result = list(self._buf[: self._count])
        else:
            start = self._write_idx & (self.capacity - 1)
            result = list(self._buf[start:]) + list(self._buf[:start])
        self._write_idx = 0
        self._count = 0
        return result


class FrameMetricsAggregator:
    """Aggregates per-frame metrics in ring buffers, flushing to OTel periodically.

    Usage on the hot path (render thread):
        aggregator.record(forward_pass_ms=11.2, render_ms=3.1)

    The flush thread (daemon) exports aggregated samples to OTel histograms.
    """

    # Metric names that map to ring buffers and their OTel instrument attrs
    METRIC_KEYS = (
        "forward_pass_ms",
        "render_ms",
        "encode_ms",
        "audio_ms",
    )

    def __init__(
        self,
        instruments: MetricInstruments,
        buffer_size: int = 512,
        flush_interval_ms: int = 1_000,
    ) -> None:
        self._instruments = instruments
        self._flush_interval_s = flush_interval_ms / 1000.0
        self._lock = threading.Lock()
        self._stop_event = threading.Event()

        self._buffers: dict[str, _RingBuffer] = {
            key: _RingBuffer(capacity=buffer_size) for key in self.METRIC_KEYS
        }

        self._thread = threading.Thread(
            target=self._flush_loop, daemon=True, name="modaltrace-flush"
        )

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        self._thread.join(timeout=5.0)
        self._flush()

    def record(self, **kwargs: float) -> None:
        """Record metric values into ring buffers. ~200ns per call."""
        with self._lock:
            for key, value in kwargs.items():
                buf = self._buffers.get(key)
                if buf is not None:
                    buf.write(value)

    def _flush_loop(self) -> None:
        while not self._stop_event.wait(timeout=self._flush_interval_s):
            try:
                self._flush()
            except Exception as exc:
                logger.exception("Metrics flush failed: %s", exc)

    def _flush(self) -> None:
        with self._lock:
            snapshots = {key: buf.drain() for key, buf in self._buffers.items()}

        instrument_map = {
            "forward_pass_ms": self._instruments.forward_pass_duration,
            "render_ms": self._instruments.render_frame_duration,
            "encode_ms": self._instruments.encode_frame_duration,
            "audio_ms": self._instruments.audio_chunk_duration,
        }

        for key, samples in snapshots.items():
            histogram = instrument_map.get(key)
            if histogram is None:
                continue
            for value in samples:
                histogram.record(value)
