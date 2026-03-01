"""Tests for GPU monitor — uses mocked pynvml."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from modaltrace.instrumentation.gpu import GPUMonitor, GPUReading


class TestGPUMonitor:
    def test_start_without_pynvml(self):
        monitor = GPUMonitor()
        with patch.dict("sys.modules", {"pynvml": None}):
            result = monitor.start()
        assert result is False

    def test_get_readings_empty_before_start(self):
        monitor = GPUMonitor()
        assert monitor.get_readings() == []

    def test_gpu_reading_defaults(self):
        reading = GPUReading()
        assert reading.device_index == 0
        assert reading.utilization_pct == 0.0
        assert reading.memory_used_mb == 0.0
        assert reading.temperature_c == 0.0
        assert reading.power_w == 0.0

    def test_stop_without_start(self):
        monitor = GPUMonitor()
        monitor.stop()  # Should not raise

    @patch("modaltrace.instrumentation.gpu.GPUMonitor._poll")
    def test_poll_called_on_start(self, mock_poll):
        """Test that with mocked pynvml, start initializes correctly."""
        mock_pynvml = MagicMock()
        mock_pynvml.nvmlInit = MagicMock()
        mock_pynvml.nvmlDeviceGetCount = MagicMock(return_value=1)
        mock_pynvml.nvmlDeviceGetHandleByIndex = MagicMock(return_value="handle0")
        mock_pynvml.nvmlShutdown = MagicMock()

        with patch.dict("sys.modules", {"pynvml": mock_pynvml}):
            monitor = GPUMonitor(poll_interval_s=0.01)
            result = monitor.start()
            assert result is True
            import time

            time.sleep(0.05)
            monitor.stop()

        assert mock_poll.call_count >= 1

    def test_register_gauges(self):
        monitor = GPUMonitor()
        # Pre-populate readings
        monitor._readings = [
            GPUReading(
                device_index=0,
                utilization_pct=75.0,
                memory_used_mb=4096.0,
                temperature_c=65.0,
            )
        ]

        mock_meter = MagicMock()
        monitor.register_gauges(mock_meter)

        assert mock_meter.create_observable_gauge.call_count == 7
