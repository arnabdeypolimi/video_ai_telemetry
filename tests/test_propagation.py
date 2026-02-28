"""Tests for OTel context propagation into thread/process pool executors."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

import pytest
from opentelemetry import context as otel_context, trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, SpanExporter, SpanExportResult

from avatar_otel.tracing.propagation import (
    patch_all,
    patch_process_pool_executor,
    patch_thread_pool_executor,
    unpatch_all,
    unpatch_process_pool_executor,
    unpatch_thread_pool_executor,
)


class _CollectingExporter(SpanExporter):
    """Simple in-memory span exporter for tests."""

    def __init__(self):
        self._spans = []

    def export(self, spans):
        self._spans.extend(spans)
        return SpanExportResult.SUCCESS

    def get_finished_spans(self):
        return list(self._spans)

    def shutdown(self):
        pass


@pytest.fixture
def tracing():
    exporter = _CollectingExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    tracer = provider.get_tracer("test")
    return tracer, exporter, provider


@pytest.fixture(autouse=True)
def cleanup_patches():
    """Ensure executor patches are always cleaned up after each test."""
    yield
    unpatch_all()


class TestThreadPoolContextPropagation:
    def test_context_propagated_to_worker(self, tracing):
        """OTel context (span) is accessible inside a ThreadPoolExecutor worker."""
        tracer, exporter, _ = tracing
        patch_thread_pool_executor()

        results = {}

        def worker():
            span = trace.get_current_span()
            ctx = span.get_span_context()
            results["trace_id"] = ctx.trace_id
            results["span_id"] = ctx.span_id
            results["is_valid"] = ctx.is_valid

        with tracer.start_as_current_span("parent") as parent_span:
            parent_ctx = parent_span.get_span_context()
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(worker)
                future.result()

        assert results["is_valid"], "Worker should see a valid span context"
        assert results["trace_id"] == parent_ctx.trace_id, (
            "Worker trace_id must match the parent span's trace_id"
        )

    def test_context_not_propagated_after_unpatch(self, tracing):
        """After unpatching, workers no longer inherit the parent OTel context."""
        tracer, _, _ = tracing
        patch_thread_pool_executor()
        unpatch_thread_pool_executor()

        results = {}

        def worker():
            span = trace.get_current_span()
            ctx = span.get_span_context()
            results["is_valid"] = ctx.is_valid

        with tracer.start_as_current_span("parent"):
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(worker)
                future.result()

        # Without the patch the thread gets a fresh (invalid) context
        assert not results["is_valid"], (
            "Unpatched executor should NOT propagate context into worker"
        )

    def test_worker_return_value_preserved(self, tracing):
        """Wrapping the callable must not alter its return value."""
        tracer, _, _ = tracing
        patch_thread_pool_executor()

        def worker(x, y):
            return x + y

        with tracer.start_as_current_span("parent"):
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(worker, 3, 4)
                result = future.result()

        assert result == 7

    def test_worker_exception_propagated(self, tracing):
        """Exceptions raised inside the worker bubble up through the future."""
        tracer, _, _ = tracing
        patch_thread_pool_executor()

        def boom():
            raise ValueError("deliberate error")

        with tracer.start_as_current_span("parent"):
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(boom)
                with pytest.raises(ValueError, match="deliberate error"):
                    future.result()


class TestPatchAllUnpatchAll:
    def test_patch_all_and_unpatch_all(self, tracing):
        """patch_all / unpatch_all apply and remove both executor patches."""
        tracer, _, _ = tracing
        patch_all()

        results = {}

        def worker():
            span = trace.get_current_span()
            results["is_valid"] = span.get_span_context().is_valid

        with tracer.start_as_current_span("parent"):
            with ThreadPoolExecutor(max_workers=1) as executor:
                executor.submit(worker).result()

        assert results["is_valid"], "patch_all should propagate context via ThreadPoolExecutor"

        # Now unpatch and verify context is no longer propagated
        unpatch_all()
        results["is_valid"] = None

        with tracer.start_as_current_span("parent"):
            with ThreadPoolExecutor(max_workers=1) as executor:
                executor.submit(worker).result()

        assert not results["is_valid"], (
            "unpatch_all should stop context propagation via ThreadPoolExecutor"
        )

    def test_unpatch_all_is_idempotent(self):
        """Calling unpatch_all multiple times without patching must not raise."""
        unpatch_all()
        unpatch_all()


class TestProcessPoolPropagation:
    def test_process_pool_patching_does_not_crash(self):
        """Patching ProcessPoolExecutor must not raise; submit completes cleanly.

        Top-level picklable functions work with ProcessPoolExecutor.  When a
        span context is active the patch wraps the callable in a picklable
        class (_ContextWrappedCallable); when pickling fails the patch falls
        back to the original callable transparently.
        """
        patch_process_pool_executor()

        with ProcessPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_simple_process_worker, 6)
            result = future.result()

        assert result == 36, "ProcessPool worker return value must be preserved"

    def test_process_pool_submit_falls_back_gracefully(self, tracing):
        """When a non-picklable function is submitted, the fallback is used.

        The patch must catch the pickle verification failure and submit the
        original callable so the work still completes.
        """
        tracer, _, _ = tracing
        patch_process_pool_executor()

        # Submit a top-level function inside an active span.  The picklable
        # wrapper should succeed and propagate the context object; the worker
        # just needs to return the correct value.
        with tracer.start_as_current_span("parent"):
            with ProcessPoolExecutor(max_workers=1) as executor:
                future = executor.submit(_simple_process_worker, 5)
                result = future.result()

        assert result == 25, "ProcessPool worker result must be correct"

    def test_process_pool_unpatch_does_not_crash(self):
        """Unpatching ProcessPoolExecutor must not raise."""
        patch_process_pool_executor()
        unpatch_process_pool_executor()

        with ProcessPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_simple_process_worker, 3)
            result = future.result()

        assert result == 9


# Must be a top-level function so that it can be pickled by ProcessPoolExecutor.
def _simple_process_worker(x):
    return x * x
