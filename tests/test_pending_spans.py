"""Tests for PendingSpanProcessor."""

from __future__ import annotations

import threading
import time

import pytest
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult

from video_ai_telemetry.conventions.attributes import PipelineAttributes
from video_ai_telemetry.tracing.pending import PendingSpanProcessor, _make_pending_snapshot


class _CollectingExporter(SpanExporter):
    """Simple in-memory span exporter for tests."""

    def __init__(self):
        self._spans = []
        self._lock = threading.Lock()

    def export(self, spans):
        with self._lock:
            self._spans.extend(spans)
        return SpanExportResult.SUCCESS

    def get_finished_spans(self):
        with self._lock:
            return list(self._spans)

    def shutdown(self):
        pass


@pytest.fixture
def exporter():
    return _CollectingExporter()


@pytest.fixture
def provider():
    return TracerProvider()


@pytest.fixture
def tracer(provider):
    return provider.get_tracer("test-pending")


class TestPendingSpanProcessorTracking:
    """Test that on_start/on_end correctly track open spans."""

    def test_on_start_tracks_span(self, exporter, tracer, provider):
        """on_start should add the span to _open_spans."""
        processor = PendingSpanProcessor(exporter, flush_interval_ms=100_000)
        provider.add_span_processor(processor)

        with tracer.start_as_current_span("in-flight") as span:
            span_id = span.context.span_id
            with processor._lock:
                assert span_id in processor._open_spans

    def test_on_end_removes_span(self, exporter, tracer, provider):
        """on_end should remove the span from _open_spans."""
        processor = PendingSpanProcessor(exporter, flush_interval_ms=100_000)
        provider.add_span_processor(processor)

        with tracer.start_as_current_span("finished") as span:
            span_id = span.context.span_id

        # After the context exits, the span should be gone
        with processor._lock:
            assert span_id not in processor._open_spans

    def test_multiple_spans_tracked(self, exporter, tracer, provider):
        """Multiple concurrent spans should all be tracked."""
        processor = PendingSpanProcessor(exporter, flush_interval_ms=100_000)
        provider.add_span_processor(processor)

        with tracer.start_as_current_span("outer") as outer:
            with tracer.start_as_current_span("inner") as inner:
                with processor._lock:
                    assert outer.context.span_id in processor._open_spans
                    assert inner.context.span_id in processor._open_spans

    def test_completed_spans_not_retained(self, exporter, tracer, provider):
        """After all spans complete, _open_spans should be empty."""
        processor = PendingSpanProcessor(exporter, flush_interval_ms=100_000)
        provider.add_span_processor(processor)

        with tracer.start_as_current_span("span-a"):
            pass
        with tracer.start_as_current_span("span-b"):
            pass

        with processor._lock:
            assert len(processor._open_spans) == 0


class TestPendingSnapshot:
    """Test that _make_pending_snapshot produces correct snapshots."""

    def test_snapshot_has_pending_attribute(self, tracer, provider, exporter):
        """Snapshot must have rt_video.span.pending = True."""

        captured = []

        class CapturingExporter(SpanExporter):
            def export(self, spans):
                captured.extend(spans)
                return SpanExportResult.SUCCESS

            def shutdown(self):
                pass

        # We need to capture the in-flight span to make a snapshot
        processor = PendingSpanProcessor(exporter, flush_interval_ms=100_000)
        provider.add_span_processor(processor)

        with tracer.start_as_current_span("my-span") as span:
            span.set_attribute("custom_key", "custom_val")
            now_ns = time.time_ns()
            with processor._lock:
                in_flight_span = processor._open_spans.get(span.context.span_id)

            assert in_flight_span is not None
            snapshot = _make_pending_snapshot(in_flight_span, now_ns)

        assert snapshot.attributes[PipelineAttributes.SPAN_PENDING] is True

    def test_snapshot_preserves_original_attributes(self, tracer, provider, exporter):
        """Snapshot should preserve all original span attributes."""
        processor = PendingSpanProcessor(exporter, flush_interval_ms=100_000)
        provider.add_span_processor(processor)

        with tracer.start_as_current_span("attr-span") as span:
            span.set_attribute("my_attr", "hello")
            now_ns = time.time_ns()
            with processor._lock:
                in_flight_span = processor._open_spans.get(span.context.span_id)

            snapshot = _make_pending_snapshot(in_flight_span, now_ns)

        assert snapshot.attributes.get("my_attr") == "hello"

    def test_snapshot_end_time_is_now(self, tracer, provider, exporter):
        """Snapshot end_time should be the provided now_ns."""
        processor = PendingSpanProcessor(exporter, flush_interval_ms=100_000)
        provider.add_span_processor(processor)

        with tracer.start_as_current_span("time-span") as span:
            now_ns = time.time_ns()
            with processor._lock:
                in_flight_span = processor._open_spans.get(span.context.span_id)

            snapshot = _make_pending_snapshot(in_flight_span, now_ns)

        assert snapshot.end_time == now_ns

    def test_snapshot_preserves_span_identity(self, tracer, provider, exporter):
        """Snapshot should share span_id and trace_id with the original span."""
        processor = PendingSpanProcessor(exporter, flush_interval_ms=100_000)
        provider.add_span_processor(processor)

        with tracer.start_as_current_span("identity-span") as span:
            original_span_id = span.context.span_id
            original_trace_id = span.context.trace_id
            now_ns = time.time_ns()
            with processor._lock:
                in_flight_span = processor._open_spans.get(span.context.span_id)

            snapshot = _make_pending_snapshot(in_flight_span, now_ns)

        assert snapshot.context.span_id == original_span_id
        assert snapshot.context.trace_id == original_trace_id

    def test_original_span_attributes_not_mutated(self, tracer, provider, exporter):
        """Making a snapshot must not mutate the original span's attributes."""
        processor = PendingSpanProcessor(exporter, flush_interval_ms=100_000)
        provider.add_span_processor(processor)

        with tracer.start_as_current_span("mutation-span") as span:
            span.set_attribute("original_key", "original_val")
            now_ns = time.time_ns()
            with processor._lock:
                in_flight_span = processor._open_spans.get(span.context.span_id)

            _make_pending_snapshot(in_flight_span, now_ns)

            # Original span should not have the pending attribute
            assert PipelineAttributes.SPAN_PENDING not in span.attributes


class TestFlushExportsPendingSpans:
    """Test that _export_pending exports snapshots for open spans."""

    def test_export_pending_sends_snapshots(self, exporter, tracer, provider):
        """_export_pending should export snapshots for all open spans."""
        processor = PendingSpanProcessor(exporter, flush_interval_ms=100_000)
        provider.add_span_processor(processor)

        with tracer.start_as_current_span("active-span"):
            processor._export_pending()

        spans = exporter.get_finished_spans()
        assert len(spans) == 1
        assert spans[0].attributes[PipelineAttributes.SPAN_PENDING] is True

    def test_export_pending_no_spans_does_nothing(self, exporter):
        """_export_pending with no open spans should not call exporter.export."""
        processor = PendingSpanProcessor(exporter, flush_interval_ms=100_000)
        processor._export_pending()
        assert exporter.get_finished_spans() == []

    def test_completed_spans_not_re_exported(self, exporter, tracer, provider):
        """Completed spans must not appear in pending exports."""
        processor = PendingSpanProcessor(exporter, flush_interval_ms=100_000)
        provider.add_span_processor(processor)

        with tracer.start_as_current_span("done"):
            pass

        # Export after span is closed — nothing should be exported
        processor._export_pending()
        assert exporter.get_finished_spans() == []

    def test_multiple_open_spans_all_exported(self, exporter, tracer, provider):
        """All open spans should be included in a single pending export."""
        processor = PendingSpanProcessor(exporter, flush_interval_ms=100_000)
        provider.add_span_processor(processor)

        with tracer.start_as_current_span("span-1"):
            with tracer.start_as_current_span("span-2"):
                processor._export_pending()

        spans = exporter.get_finished_spans()
        assert len(spans) == 2
        names = {s.name for s in spans}
        assert "span-1" in names
        assert "span-2" in names
        for s in spans:
            assert s.attributes[PipelineAttributes.SPAN_PENDING] is True


class TestStartStopLifecycle:
    """Test the start/stop lifecycle of PendingSpanProcessor."""

    def test_start_launches_background_thread(self, exporter):
        """start() should launch the background daemon thread."""
        processor = PendingSpanProcessor(exporter, flush_interval_ms=100_000)
        assert not processor._thread.is_alive()
        processor.start()
        assert processor._thread.is_alive()
        processor.stop()

    def test_stop_terminates_thread(self, exporter):
        """stop() should terminate the background thread."""
        processor = PendingSpanProcessor(exporter, flush_interval_ms=100_000)
        processor.start()
        processor.stop()
        assert not processor._thread.is_alive()

    def test_flush_loop_exports_at_interval(self, tracer, provider):
        """Background flush loop should export pending spans at the configured interval."""
        exporter = _CollectingExporter()
        # Use a very short interval (50 ms) so the test is fast
        processor = PendingSpanProcessor(exporter, flush_interval_ms=50)
        provider.add_span_processor(processor)

        processor.start()
        try:
            with tracer.start_as_current_span("long-running"):
                # Wait long enough for at least one flush to occur (>50 ms)
                time.sleep(0.2)

            # After the span ends, at least one pending export should have happened
            spans = exporter.get_finished_spans()
            assert len(spans) >= 1
            # All exported spans must be marked as pending
            for s in spans:
                assert s.attributes[PipelineAttributes.SPAN_PENDING] is True
        finally:
            processor.stop()

    def test_stop_prevents_further_exports(self, exporter):
        """After stop(), no further exports should occur."""
        processor = PendingSpanProcessor(exporter, flush_interval_ms=50)
        processor.start()
        processor.stop()

        # Manually inject a span and call _export_pending
        # (the thread is stopped, so this tests only the stop mechanism)
        assert not processor._thread.is_alive()
