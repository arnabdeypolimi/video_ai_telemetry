"""Pipeline stage tracing — @pipeline_stage decorator and stage() context manager.

Two interfaces over one implementation. Yields StageContext (not raw OTel span)
for a stable public API. Yields _NoOpStageContext when the sampler skips.
"""

from __future__ import annotations

import functools
import inspect
import time
from collections.abc import AsyncGenerator, Callable, Generator
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass, field
from typing import Any, ParamSpec, TypeVar

from opentelemetry import trace
from opentelemetry.trace import StatusCode

from modaltrace.conventions.attributes import PipelineAttributes
from modaltrace.tracing.sampler import AdaptiveSampler

P = ParamSpec("P")
R = TypeVar("R")


@dataclass
class StageContext:
    """Public interface for an active pipeline stage span."""

    _span: trace.Span
    _attributes: dict[str, Any] = field(default_factory=dict)

    def set_attribute(self, key: str, value: Any) -> None:
        self._span.set_attribute(key, value)

    def record(self, key: str, value: Any) -> None:
        self._span.set_attribute(key, value)

    @property
    def span(self) -> trace.Span:
        return self._span


@dataclass
class _NoOpStageContext:
    """No-op context returned when the sampler skips this stage."""

    def set_attribute(self, key: str, value: Any) -> None:
        pass

    def record(self, key: str, value: Any) -> None:
        pass

    @property
    def span(self) -> None:
        return None


def pipeline_stage(
    stage_name: str,
    *,
    always_trace: bool = False,
    tracer: trace.Tracer | None = None,
    sampler: AdaptiveSampler | None = None,
) -> Callable:
    """Decorator to instrument a pipeline stage function.

    Detects async at decoration time (not per-call) for zero runtime branch.
    """

    def decorator(fn: Callable[P, R]) -> Callable[P, R]:
        is_async = inspect.iscoroutinefunction(fn)

        if is_async:

            @functools.wraps(fn)
            async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
                _sampler = sampler or _get_default_sampler()
                _tracer = tracer or _get_default_tracer()

                if not _sampler.should_sample(stage_name, always_trace=always_trace):
                    return await fn(*args, **kwargs)

                with _tracer.start_as_current_span(f"modaltrace.{stage_name}") as span:
                    span.set_attribute(PipelineAttributes.STAGE_NAME, stage_name)
                    start = time.perf_counter()
                    try:
                        result = await fn(*args, **kwargs)
                        return result
                    except Exception as exc:
                        span.set_status(StatusCode.ERROR, str(exc))
                        span.record_exception(exc)
                        raise
                    finally:
                        elapsed_ms = (time.perf_counter() - start) * 1000
                        span.set_attribute(PipelineAttributes.STAGE_DURATION_MS, elapsed_ms)

            return async_wrapper  # type: ignore[return-value]
        else:

            @functools.wraps(fn)
            def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
                _sampler = sampler or _get_default_sampler()
                _tracer = tracer or _get_default_tracer()

                if not _sampler.should_sample(stage_name, always_trace=always_trace):
                    return fn(*args, **kwargs)

                with _tracer.start_as_current_span(f"modaltrace.{stage_name}") as span:
                    span.set_attribute(PipelineAttributes.STAGE_NAME, stage_name)
                    start = time.perf_counter()
                    try:
                        result = fn(*args, **kwargs)
                        return result
                    except Exception as exc:
                        span.set_status(StatusCode.ERROR, str(exc))
                        span.record_exception(exc)
                        raise
                    finally:
                        elapsed_ms = (time.perf_counter() - start) * 1000
                        span.set_attribute(PipelineAttributes.STAGE_DURATION_MS, elapsed_ms)

            return sync_wrapper  # type: ignore[return-value]

    return decorator


@contextmanager
def stage(
    stage_name: str,
    *,
    tracer: trace.Tracer | None = None,
    sampler: AdaptiveSampler | None = None,
    always_trace: bool = False,
    **attrs: Any,
) -> Generator[StageContext | _NoOpStageContext, None, None]:
    """Synchronous context manager for pipeline stage tracing."""
    _sampler = sampler or _get_default_sampler()
    _tracer = tracer or _get_default_tracer()

    if not _sampler.should_sample(stage_name, always_trace=always_trace):
        yield _NoOpStageContext()
        return

    with _tracer.start_as_current_span(f"modaltrace.{stage_name}") as span:
        span.set_attribute(PipelineAttributes.STAGE_NAME, stage_name)
        for key, value in attrs.items():
            span.set_attribute(key, value)
        ctx = StageContext(_span=span)
        start = time.perf_counter()
        try:
            yield ctx
        except Exception as exc:
            span.set_status(StatusCode.ERROR, str(exc))
            span.record_exception(exc)
            raise
        finally:
            elapsed_ms = (time.perf_counter() - start) * 1000
            span.set_attribute(PipelineAttributes.STAGE_DURATION_MS, elapsed_ms)


@asynccontextmanager
async def async_stage(
    stage_name: str,
    *,
    tracer: trace.Tracer | None = None,
    sampler: AdaptiveSampler | None = None,
    always_trace: bool = False,
    **attrs: Any,
) -> AsyncGenerator[StageContext | _NoOpStageContext, None]:
    """Async context manager for pipeline stage tracing."""
    _sampler = sampler or _get_default_sampler()
    _tracer = tracer or _get_default_tracer()

    if not _sampler.should_sample(stage_name, always_trace=always_trace):
        yield _NoOpStageContext()
        return

    with _tracer.start_as_current_span(f"modaltrace.{stage_name}") as span:
        span.set_attribute(PipelineAttributes.STAGE_NAME, stage_name)
        for key, value in attrs.items():
            span.set_attribute(key, value)
        ctx = StageContext(_span=span)
        start = time.perf_counter()
        try:
            yield ctx
        except Exception as exc:
            span.set_status(StatusCode.ERROR, str(exc))
            span.record_exception(exc)
            raise
        finally:
            elapsed_ms = (time.perf_counter() - start) * 1000
            span.set_attribute(PipelineAttributes.STAGE_DURATION_MS, elapsed_ms)


def _get_default_tracer() -> trace.Tracer:
    from modaltrace import _registry

    if _registry._tracer is not None:
        return _registry._tracer
    return trace.get_tracer("modaltrace")


def _get_default_sampler() -> AdaptiveSampler:
    from modaltrace import _registry

    if hasattr(_registry, "_sampler") and _registry._sampler is not None:
        return _registry._sampler
    return AdaptiveSampler()
