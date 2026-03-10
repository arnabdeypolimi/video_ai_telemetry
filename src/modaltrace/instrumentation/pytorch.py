"""PyTorch auto-instrumentation via wrapt.

Patches torch.nn.Module.__call__ with two-tier recording:
- Every forward() call: record timing to ring buffer (~200ns)
- 1% of calls (or slow outliers): create full OTel span with details
"""

from __future__ import annotations

import logging
import random
import time
from typing import Any

from modaltrace.conventions.attributes import InferenceAttributes
from modaltrace.conventions.namespaces import NAMESPACE as _NS

logger = logging.getLogger(f"{_NS}.pytorch")

_original_module_call = None
_tracer = None
_sampler_rate: float = 0.01
_anomaly_threshold_ms: float = 50.0
_track_memory: bool = True
_track_shapes: bool = False
_aggregator = None


def instrument_pytorch(
    tracer: Any = None,
    sample_rate: float = 0.01,
    anomaly_threshold_ms: float = 50.0,
    track_memory: bool = True,
    track_shapes: bool = False,
    aggregator: Any = None,
) -> bool:
    """Patch torch.nn.Module.__call__ for instrumentation.

    Returns True if patching succeeded, False if torch is unavailable.
    """
    global _original_module_call, _tracer, _sampler_rate
    global _anomaly_threshold_ms, _track_memory, _track_shapes, _aggregator

    try:
        import torch
    except ImportError:
        logger.debug("PyTorch not available, skipping instrumentation")
        return False

    if _original_module_call is not None:
        logger.debug("PyTorch already instrumented")
        return True

    _tracer = tracer
    _sampler_rate = sample_rate
    _anomaly_threshold_ms = anomaly_threshold_ms
    _track_memory = track_memory
    _track_shapes = track_shapes
    _aggregator = aggregator

    _original_module_call = torch.nn.Module.__call__

    def patched_call(self, *args, **kwargs):
        return _instrumented_call(self, *args, **kwargs)

    torch.nn.Module.__call__ = patched_call
    logger.debug("PyTorch instrumentation installed")
    return True


def uninstrument_pytorch() -> None:
    """Restore the original torch.nn.Module.__call__."""
    global _original_module_call

    if _original_module_call is None:
        return

    try:
        import torch

        torch.nn.Module.__call__ = _original_module_call
        _original_module_call = None
        logger.debug("PyTorch instrumentation removed")
    except ImportError:
        _original_module_call = None


def _instrumented_call(module, *args, **kwargs):
    """Instrumented wrapper for Module.__call__."""
    import torch

    model_name = module.__class__.__name__

    # Memory tracking before call
    mem_before: float | None = None
    if _track_memory and torch.cuda.is_available():
        try:
            mem_before = torch.cuda.memory_allocated() / (1024 * 1024)
        except Exception:
            pass

    start = time.perf_counter_ns()
    result = None
    exception_raised = False

    try:
        result = _original_module_call(module, *args, **kwargs)
    except Exception:
        exception_raised = True
        raise
    finally:
        elapsed_ns = time.perf_counter_ns() - start
        elapsed_ms = elapsed_ns / 1e6

        # Tier 1: Always record to ring buffer (~200ns)
        if _aggregator is not None:
            _aggregator.record(forward_pass_ms=elapsed_ms)

        # Tier 2: Span creation for sampled or slow calls
        should_span = (
            random.random() < _sampler_rate
            or elapsed_ms > _anomaly_threshold_ms
            or exception_raised
        )

        if should_span and _tracer is not None:
            with _tracer.start_as_current_span(f"modaltrace.torch.{model_name}") as span:
                span.set_attribute(InferenceAttributes.MODEL_NAME, model_name)
                span.set_attribute(InferenceAttributes.FORWARD_PASS_MS, elapsed_ms)

                # Device info
                try:
                    params = list(module.parameters())
                    if params:
                        device = str(params[0].device)
                        span.set_attribute(InferenceAttributes.DEVICE, device)
                except Exception:
                    pass

                # Memory delta
                if mem_before is not None:
                    try:
                        mem_after = torch.cuda.memory_allocated() / (1024 * 1024)
                        span.set_attribute(InferenceAttributes.GPU_MEMORY_MB, mem_after)
                        span.set_attribute(
                            InferenceAttributes.GPU_MEMORY_DELTA_MB, mem_after - mem_before
                        )
                    except Exception:
                        pass

                # Shape capture (off by default — PII risk)
                if _track_shapes:
                    shapes = []
                    for arg in args:
                        if isinstance(arg, torch.Tensor):
                            shapes.append(str(list(arg.shape)))
                    if shapes:
                        span.set_attribute(InferenceAttributes.INPUT_SHAPES, str(shapes))

    return result
