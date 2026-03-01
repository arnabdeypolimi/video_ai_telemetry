"""PendingSpanProcessor — exports snapshots of currently-open (in-flight) spans.

Exports a ReadableSpan-like snapshot at a fixed interval for each open span,
marking each snapshot with modaltrace.span.pending = True so backends can
distinguish pending snapshots from completed spans.
"""

from __future__ import annotations

import logging
import threading
import time

from opentelemetry.sdk.trace import ReadableSpan, SpanProcessor
from opentelemetry.sdk.trace.export import SpanExporter

from modaltrace.conventions.attributes import PipelineAttributes

logger = logging.getLogger("modaltrace.pending")


def _make_pending_snapshot(span: ReadableSpan, now_ns: int) -> ReadableSpan:
    """Return a ReadableSpan snapshot of an in-flight span.

    The snapshot has:
    - The same metadata as the original span.
    - ``end_time`` set to ``now_ns`` (artificial end time for the snapshot).
    - ``modaltrace.span.pending = True`` added to attributes.
    """
    attrs_copy: dict = dict(span.attributes) if span.attributes else {}
    attrs_copy[PipelineAttributes.SPAN_PENDING] = True

    return ReadableSpan(
        name=span.name,
        context=span.context,
        parent=span.parent,
        resource=span.resource,
        attributes=attrs_copy,
        events=span.events,
        links=span.links,
        kind=span.kind,
        instrumentation_scope=span.instrumentation_scope,
        status=span.status,
        start_time=span.start_time,
        end_time=now_ns,
    )


class PendingSpanProcessor(SpanProcessor):
    """Exports a snapshot of all currently-open spans at a fixed interval.

    The snapshot is a copy with the current timestamp as an artificial
    end_time, marked with modaltrace.span.pending = True so backends can
    distinguish pending snapshots from completed spans.

    Usage::

        exporter = OTLPSpanExporter(...)
        processor = PendingSpanProcessor(exporter, flush_interval_ms=5_000)
        processor.start()

        provider = TracerProvider()
        provider.add_span_processor(processor)

        # When done:
        processor.stop()
    """

    def __init__(self, exporter: SpanExporter, flush_interval_ms: int = 5_000) -> None:
        self._exporter = exporter
        self._interval_s = flush_interval_ms / 1000.0
        self._open_spans: dict[int, ReadableSpan] = {}  # span_id -> span
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._flush_loop, daemon=True)

    # --- SpanProcessor interface ---

    def on_start(self, span: ReadableSpan, parent_context=None) -> None:
        """Track the span as soon as it starts."""
        with self._lock:
            self._open_spans[span.context.span_id] = span

    def on_end(self, span: ReadableSpan) -> None:
        """Remove the span from tracking when it ends."""
        with self._lock:
            self._open_spans.pop(span.context.span_id, None)

    # --- Lifecycle ---

    def start(self) -> None:
        """Start the background flush thread."""
        self._thread.start()

    def stop(self) -> None:
        """Signal the flush thread to stop and wait for it to finish."""
        self._stop.set()
        self._thread.join(timeout=5.0)

    def shutdown(self) -> None:
        """Shut down the processor; stops the background thread if running."""
        if self._thread.is_alive():
            self.stop()

    def force_flush(self, timeout_millis: int = 30_000) -> bool:
        """Immediately export all pending spans; returns True on success."""
        self._export_pending()
        return True

    # --- Internal ---

    def _flush_loop(self) -> None:
        """Background loop: wait for interval then export pending snapshots."""
        while not self._stop.wait(timeout=self._interval_s):
            try:
                self._export_pending()
            except Exception as exc:
                logger.exception("Failed to export pending spans: %s", exc)

    def _export_pending(self) -> None:
        """Take a snapshot of all open spans and export them."""
        with self._lock:
            open_spans = list(self._open_spans.values())

        if not open_spans:
            return

        now_ns = time.time_ns()
        snapshots = [_make_pending_snapshot(span, now_ns) for span in open_spans]
        try:
            self._exporter.export(snapshots)
        except Exception as exc:
            logger.exception("Pending span exporter failed: %s", exc)
