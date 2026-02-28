"""Context propagation helpers for concurrent execution.

Patches :class:`concurrent.futures.ThreadPoolExecutor` and
:class:`concurrent.futures.ProcessPoolExecutor` so that the active
OpenTelemetry context is automatically propagated into submitted workers.

ThreadPoolExecutor workers share memory with the parent process, so OTel
context objects are propagated via a simple closure.

ProcessPoolExecutor workers run in separate processes.  Closures are not
picklable, so a picklable wrapper class is used instead.  If pickling still
fails for any reason the original callable is submitted unchanged and a debug
message is logged.
"""

from __future__ import annotations

import logging
import pickle
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor

from opentelemetry import context as otel_context

logger = logging.getLogger("video_ai_telemetry.propagation")
_original_thread_submit = None
_original_process_submit = None


# ---------------------------------------------------------------------------
# Picklable callable wrapper for ProcessPoolExecutor
# ---------------------------------------------------------------------------


class _ContextWrappedCallable:
    """A picklable wrapper that re-attaches an OTel context before calling fn.

    OTel context objects are plain dicts internally; they can be pickled as
    long as none of the values stored inside them prevent pickling.  If the
    context cannot be pickled the :func:`patch_process_pool_executor` helper
    falls back to submitting the original callable.
    """

    __slots__ = ("_fn", "_ctx")

    def __init__(self, fn, ctx):
        self._fn = fn
        self._ctx = ctx

    def __call__(self, *args, **kwargs):
        token = otel_context.attach(self._ctx)
        try:
            return self._fn(*args, **kwargs)
        finally:
            otel_context.detach(token)


# ---------------------------------------------------------------------------
# ThreadPoolExecutor patch
# ---------------------------------------------------------------------------


def patch_thread_pool_executor():
    global _original_thread_submit
    _original_thread_submit = ThreadPoolExecutor.submit

    def patched_submit(self, fn, /, *args, **kwargs):
        current_ctx = otel_context.get_current()

        def wrapped_fn(*a, **kw):
            token = otel_context.attach(current_ctx)
            try:
                return fn(*a, **kw)
            finally:
                otel_context.detach(token)

        return _original_thread_submit(self, wrapped_fn, *args, **kwargs)

    ThreadPoolExecutor.submit = patched_submit


def unpatch_thread_pool_executor():
    global _original_thread_submit
    if _original_thread_submit is not None:
        ThreadPoolExecutor.submit = _original_thread_submit
        _original_thread_submit = None


# ---------------------------------------------------------------------------
# ProcessPoolExecutor patch
# ---------------------------------------------------------------------------


def patch_process_pool_executor():
    global _original_process_submit
    _original_process_submit = ProcessPoolExecutor.submit

    def patched_submit(self, fn, /, *args, **kwargs):
        try:
            current_ctx = otel_context.get_current()
            wrapped = _ContextWrappedCallable(fn, current_ctx)
            # Verify the wrapped callable is picklable before submitting so
            # that we can fall back gracefully rather than getting an opaque
            # error from the worker queue.
            pickle.dumps(wrapped)
            return _original_process_submit(self, wrapped, *args, **kwargs)
        except Exception as exc:
            logger.debug("ProcessPool context propagation failed: %s", exc)
            return _original_process_submit(self, fn, *args, **kwargs)

    ProcessPoolExecutor.submit = patched_submit


def unpatch_process_pool_executor():
    global _original_process_submit
    if _original_process_submit is not None:
        ProcessPoolExecutor.submit = _original_process_submit
        _original_process_submit = None


# ---------------------------------------------------------------------------
# Convenience helpers
# ---------------------------------------------------------------------------


def patch_all():
    patch_thread_pool_executor()
    patch_process_pool_executor()


def unpatch_all():
    unpatch_thread_pool_executor()
    unpatch_process_pool_executor()
