"""Tests for event loop blocking monitor."""
from __future__ import annotations

import asyncio
import time

import pytest

from avatar_otel.instrumentation.eventloop import (
    install_eventloop_monitor,
    uninstall_eventloop_monitor,
)


def test_patch_applied_and_removed():
    """Test that the patch is applied and removed correctly."""
    import asyncio.events

    original_run = asyncio.events.Handle._run

    install_eventloop_monitor(threshold_ms=100.0)

    patched_run = asyncio.events.Handle._run
    assert patched_run is not original_run, "Patch was not applied"

    uninstall_eventloop_monitor()

    restored_run = asyncio.events.Handle._run
    assert restored_run is original_run, "Original was not restored after uninstall"


def test_blocking_handle_triggers_callback():
    """Test that a blocking handle triggers the warning callback."""
    warnings = []

    def my_callback(msg, **kwargs):
        warnings.append({"msg": msg, **kwargs})

    install_eventloop_monitor(threshold_ms=50.0, warning_callback=my_callback)

    try:
        loop = asyncio.new_event_loop()

        async def blocking_coro():
            time.sleep(0.15)  # 150ms > 50ms threshold

        loop.run_until_complete(blocking_coro())
        loop.close()
    finally:
        uninstall_eventloop_monitor()

    assert len(warnings) >= 1, "Warning callback was not called for blocking handle"
    assert warnings[0]["elapsed_ms"] > 50.0
    assert warnings[0]["threshold_ms"] == 50.0
    assert "Event loop blocked" in warnings[0]["msg"]


def test_fast_handle_does_not_trigger_callback():
    """Test that a fast handle does NOT trigger the warning callback."""
    warnings = []

    def my_callback(msg, **kwargs):
        warnings.append({"msg": msg, **kwargs})

    install_eventloop_monitor(threshold_ms=200.0, warning_callback=my_callback)

    try:
        loop = asyncio.new_event_loop()

        async def fast_coro():
            await asyncio.sleep(0)  # yields control, very fast

        loop.run_until_complete(fast_coro())
        loop.close()
    finally:
        uninstall_eventloop_monitor()

    assert len(warnings) == 0, f"Warning callback was unexpectedly called: {warnings}"


def test_uninstall_restores_original_behavior():
    """Test that uninstall restores original behavior (no more monitoring)."""
    import asyncio.events

    original_run = asyncio.events.Handle._run

    install_eventloop_monitor(threshold_ms=10.0)
    uninstall_eventloop_monitor()

    assert asyncio.events.Handle._run is original_run

    # Confirm no side effects after uninstall even if a blocking call is made
    loop = asyncio.new_event_loop()

    async def blocking_coro():
        time.sleep(0.05)

    loop.run_until_complete(blocking_coro())
    loop.close()

    # Still restored
    assert asyncio.events.Handle._run is original_run


def test_uninstall_is_idempotent():
    """Test that calling uninstall multiple times is safe."""
    install_eventloop_monitor(threshold_ms=100.0)
    uninstall_eventloop_monitor()
    uninstall_eventloop_monitor()  # should not raise


def test_default_logger_warning(caplog):
    """Test that the default logger is used when no callback is provided."""
    import logging

    install_eventloop_monitor(threshold_ms=50.0, warning_callback=None)

    try:
        with caplog.at_level(logging.WARNING, logger="avatar_otel.eventloop"):
            loop = asyncio.new_event_loop()

            async def blocking_coro():
                time.sleep(0.15)

            loop.run_until_complete(blocking_coro())
            loop.close()
    finally:
        uninstall_eventloop_monitor()

    assert any("Event loop blocked" in r.message for r in caplog.records), (
        "Expected warning log not found"
    )
