from __future__ import annotations

import asyncio
import logging
import time

logger = logging.getLogger("modaltrace.eventloop")

_original_handle_run = None
_warning_callback = None


def install_eventloop_monitor(
    threshold_ms: float = 100.0,
    warning_callback=None,
):
    global _original_handle_run, _warning_callback
    _original_handle_run = asyncio.events.Handle._run
    _warning_callback = warning_callback

    def patched_run(self):
        start = time.perf_counter()
        try:
            _original_handle_run(self)
        finally:
            elapsed_ms = (time.perf_counter() - start) * 1000
            if elapsed_ms > threshold_ms:
                cb_name = getattr(self._callback, "__qualname__", str(self._callback))
                if _warning_callback:
                    _warning_callback(
                        "Event loop blocked for {elapsed_ms:.1f}ms by {handle_callback}",
                        elapsed_ms=elapsed_ms,
                        threshold_ms=threshold_ms,
                        handle_callback=cb_name,
                    )
                else:
                    logger.warning("Event loop blocked for %.1fms by %s", elapsed_ms, cb_name)

    asyncio.events.Handle._run = patched_run


def uninstall_eventloop_monitor():
    global _original_handle_run, _warning_callback
    if _original_handle_run is not None:
        asyncio.events.Handle._run = _original_handle_run
        _original_handle_run = None
        _warning_callback = None
