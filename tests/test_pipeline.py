"""Tests for pipeline stage tracing — decorator and context manager."""

from __future__ import annotations

import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, SpanExporter, SpanExportResult

from modaltrace.conventions.attributes import PipelineAttributes
from modaltrace.tracing.pipeline import (
    StageContext,
    _NoOpStageContext,
    async_stage,
    pipeline_stage,
    stage,
)
from modaltrace.tracing.sampler import AdaptiveSampler


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


@pytest.fixture
def always_sampler():
    return AdaptiveSampler(window_s=0.0)


class TestPipelineStageDecorator:
    def test_sync_function(self, tracing, always_sampler):
        tracer, exporter, _ = tracing

        @pipeline_stage("render", tracer=tracer, sampler=always_sampler)
        def render_frame(data: str) -> str:
            return f"rendered:{data}"

        result = render_frame("test")
        assert result == "rendered:test"

        spans = exporter.get_finished_spans()
        assert len(spans) == 1
        assert spans[0].name == "modaltrace.render"
        assert spans[0].attributes[PipelineAttributes.STAGE_NAME] == "render"
        assert PipelineAttributes.STAGE_DURATION_MS in spans[0].attributes

    @pytest.mark.asyncio
    async def test_async_function(self, tracing, always_sampler):
        tracer, exporter, _ = tracing

        @pipeline_stage("ingest", tracer=tracer, sampler=always_sampler)
        async def ingest_audio(data: bytes) -> str:
            return f"ingested:{len(data)}"

        result = await ingest_audio(b"audio")
        assert result == "ingested:5"

        spans = exporter.get_finished_spans()
        assert len(spans) == 1
        assert spans[0].name == "modaltrace.ingest"

    def test_exception_recorded(self, tracing, always_sampler):
        tracer, exporter, _ = tracing

        @pipeline_stage("broken", tracer=tracer, sampler=always_sampler)
        def broken_stage() -> None:
            raise ValueError("test error")

        with pytest.raises(ValueError, match="test error"):
            broken_stage()

        spans = exporter.get_finished_spans()
        assert len(spans) == 1
        assert spans[0].status.status_code == trace.StatusCode.ERROR
        assert any(e.name == "exception" for e in spans[0].events)

    def test_sampler_skips(self, tracing):
        tracer, exporter, _ = tracing
        never_sampler = AdaptiveSampler(window_s=999.0)
        never_sampler.should_sample("skip_test")

        @pipeline_stage("skip_test", tracer=tracer, sampler=never_sampler)
        def skipped() -> str:
            return "ok"

        result = skipped()
        assert result == "ok"
        assert len(exporter.get_finished_spans()) == 0


class TestStageContextManager:
    def test_sync_stage(self, tracing, always_sampler):
        tracer, exporter, _ = tracing

        with stage("encode", tracer=tracer, sampler=always_sampler) as s:
            assert isinstance(s, StageContext)
            s.record("bitrate_kbps", 2400)

        spans = exporter.get_finished_spans()
        assert len(spans) == 1
        assert spans[0].attributes["bitrate_kbps"] == 2400

    @pytest.mark.asyncio
    async def test_async_stage(self, tracing, always_sampler):
        tracer, exporter, _ = tracing

        async with async_stage("decode", tracer=tracer, sampler=always_sampler) as s:
            s.set_attribute("codec", "h264")

        spans = exporter.get_finished_spans()
        assert len(spans) == 1
        assert spans[0].attributes["codec"] == "h264"

    def test_noop_when_not_sampled(self, tracing):
        tracer, exporter, _ = tracing
        never_sampler = AdaptiveSampler(window_s=999.0)
        never_sampler.should_sample("noop_test")

        with stage("noop_test", tracer=tracer, sampler=never_sampler) as s:
            assert isinstance(s, _NoOpStageContext)
            s.record("anything", 42)

        assert len(exporter.get_finished_spans()) == 0

    def test_exception_in_stage(self, tracing, always_sampler):
        tracer, exporter, _ = tracing

        with pytest.raises(RuntimeError, match="boom"):
            with stage("explode", tracer=tracer, sampler=always_sampler):
                raise RuntimeError("boom")

        spans = exporter.get_finished_spans()
        assert len(spans) == 1
        assert spans[0].status.status_code == trace.StatusCode.ERROR
