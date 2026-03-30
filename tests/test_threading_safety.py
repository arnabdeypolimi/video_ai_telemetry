"""Tests for thread safety of instrumentation and tracking components.

These tests validate that concurrent operations don't cause race conditions.
"""

from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import MagicMock, patch

import pytest

from modaltrace.instrumentation.gpu import GPUMonitor, GPUReading
from modaltrace.instrumentation.pytorch import instrument_pytorch, uninstrument_pytorch
from modaltrace.metrics.av_sync import AVSyncTracker


class TestPyTorchThreadSafety:
    """Test thread safety of PyTorch instrumentation."""

    def setup_method(self):
        uninstrument_pytorch()

    def teardown_method(self):
        uninstrument_pytorch()

    def test_concurrent_instrument_uninstrument(self):
        """Test that concurrent instrument/uninstrument calls don't race."""
        mock_torch = MagicMock()
        mock_torch.nn.Module.__call__ = lambda self, *args, **kwargs: "output"
        mock_torch.cuda.is_available.return_value = False

        errors = []
        iterations = 100

        def instrument_cycle():
            try:
                for _ in range(iterations):
                    with patch.dict("sys.modules", {"torch": mock_torch}):
                        instrument_pytorch()
                        uninstrument_pytorch()
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=instrument_cycle) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Errors occurred: {errors}"

    def test_concurrent_instrument_same_time(self):
        """Test that multiple threads calling instrument at once is safe."""
        mock_torch = MagicMock()
        mock_torch.nn.Module.__call__ = lambda self, *args, **kwargs: "output"
        mock_torch.cuda.is_available.return_value = False

        results = []
        barrier = threading.Barrier(10)

        def try_instrument():
            barrier.wait()  # All threads start at the same time
            with patch.dict("sys.modules", {"torch": mock_torch}):
                result = instrument_pytorch()
                results.append(result)

        threads = [threading.Thread(target=try_instrument) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All should succeed (first one patches, rest are no-ops)
        assert all(r is True for r in results)


class TestGPUMonitorThreadSafety:
    """Test thread safety of GPU monitor operations."""

    def test_concurrent_get_readings_during_poll(self):
        """Test that get_readings is safe while _poll is running."""
        monitor = GPUMonitor(poll_interval_s=0.001)

        # Pre-populate with some readings
        monitor._readings = [
            GPUReading(device_index=0, utilization_pct=50.0),
            GPUReading(device_index=1, utilization_pct=60.0),
        ]

        errors = []
        stop_event = threading.Event()

        def poll_loop():
            """Simulate continuous polling."""
            while not stop_event.is_set():
                with monitor._lock:
                    monitor._readings = [
                        GPUReading(device_index=0, utilization_pct=50.0 + (time.time() % 10)),
                    ]
                time.sleep(0.001)

        def read_loop():
            """Continuously read readings."""
            try:
                for _ in range(100):
                    readings = monitor.get_readings()
                    # Should always get a valid list
                    assert isinstance(readings, list)
                    for r in readings:
                        assert isinstance(r, GPUReading)
            except Exception as e:
                errors.append(e)

        poll_thread = threading.Thread(target=poll_loop)
        read_threads = [threading.Thread(target=read_loop) for _ in range(4)]

        poll_thread.start()
        for t in read_threads:
            t.start()

        for t in read_threads:
            t.join()
        stop_event.set()
        poll_thread.join()

        assert len(errors) == 0, f"Errors occurred: {errors}"

    def test_concurrent_start_stop(self):
        """Test that concurrent start/stop calls are safe."""
        errors = []
        iterations = 20

        def start_stop_cycle():
            try:
                for _ in range(iterations):
                    mock_pynvml = MagicMock()
                    mock_pynvml.nvmlInit = MagicMock()
                    mock_pynvml.nvmlDeviceGetCount = MagicMock(return_value=1)
                    mock_pynvml.nvmlDeviceGetHandleByIndex = MagicMock(return_value="handle")
                    mock_pynvml.nvmlShutdown = MagicMock()

                    monitor = GPUMonitor(poll_interval_s=0.01)
                    with patch.dict("sys.modules", {"pynvml": mock_pynvml}):
                        monitor.start()
                        time.sleep(0.005)
                        monitor.stop()
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=start_stop_cycle) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Errors occurred: {errors}"


class TestAVSyncTrackerThreadSafety:
    """Test thread safety of AVSyncTracker operations."""

    @pytest.fixture
    def mock_instruments(self):
        instruments = MagicMock()
        instruments.av_sync_drift = MagicMock()
        instruments.av_sync_jitter = MagicMock()
        instruments.av_sync_unmatched = MagicMock()
        return instruments

    def test_concurrent_audio_captured_frame_rendered(self, mock_instruments):
        """Test concurrent audio_captured and frame_rendered calls."""
        tracker = AVSyncTracker(instruments=mock_instruments, chunk_ttl_s=10.0)
        errors = []
        num_chunks = 1000

        def producer():
            """Add audio chunks."""
            try:
                for i in range(num_chunks):
                    tracker.audio_captured(chunk_id=i)
            except Exception as e:
                errors.append(("producer", e))

        def consumer():
            """Consume chunks with frame_rendered."""
            try:
                for i in range(num_chunks):
                    # May return None if chunk not yet added or already consumed
                    tracker.frame_rendered(chunk_id=i)
            except Exception as e:
                errors.append(("consumer", e))

        # Run producers and consumers concurrently
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = []
            futures.extend([executor.submit(producer) for _ in range(2)])
            futures.extend([executor.submit(consumer) for _ in range(4)])

            for f in as_completed(futures):
                f.result()  # Raise any exceptions

        assert len(errors) == 0, f"Errors occurred: {errors}"

    def test_concurrent_cleanup_with_operations(self, mock_instruments):
        """Test that cleanup_expired is safe during other operations."""
        tracker = AVSyncTracker(
            instruments=mock_instruments,
            chunk_ttl_s=0.001,  # Very short TTL
        )
        errors = []
        stop_event = threading.Event()

        def add_chunks():
            chunk_id = 0
            while not stop_event.is_set():
                try:
                    tracker.audio_captured(chunk_id=chunk_id)
                    chunk_id += 1
                    time.sleep(0.0001)
                except Exception as e:
                    errors.append(("add", e))

        def render_chunks():
            chunk_id = 0
            while not stop_event.is_set():
                try:
                    tracker.frame_rendered(chunk_id=chunk_id)
                    chunk_id += 1
                    time.sleep(0.0001)
                except Exception as e:
                    errors.append(("render", e))

        def cleanup_loop():
            while not stop_event.is_set():
                try:
                    tracker.cleanup_expired()
                    time.sleep(0.001)
                except Exception as e:
                    errors.append(("cleanup", e))

        threads = [
            threading.Thread(target=add_chunks),
            threading.Thread(target=add_chunks),
            threading.Thread(target=render_chunks),
            threading.Thread(target=render_chunks),
            threading.Thread(target=cleanup_loop),
        ]

        for t in threads:
            t.start()

        time.sleep(0.1)  # Run for 100ms
        stop_event.set()

        for t in threads:
            t.join()

        assert len(errors) == 0, f"Errors occurred: {errors}"

    def test_high_contention_drift_window(self, mock_instruments):
        """Test drift window updates under high contention."""
        tracker = AVSyncTracker(
            instruments=mock_instruments,
            jitter_window=100,
            chunk_ttl_s=60.0,
        )
        errors = []
        chunk_counter = [0]
        counter_lock = threading.Lock()

        def measure_drift():
            try:
                for _ in range(200):
                    with counter_lock:
                        chunk_id = chunk_counter[0]
                        chunk_counter[0] += 1

                    tracker.audio_captured(chunk_id=chunk_id)
                    time.sleep(0.0001)
                    tracker.frame_rendered(chunk_id=chunk_id)

                    # Access properties (should not raise)
                    _ = tracker.current_drift_ms
                    _ = tracker.current_jitter_ms
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=measure_drift) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Errors occurred: {errors}"
        # Verify some measurements were recorded
        assert mock_instruments.av_sync_drift.record.call_count > 0
