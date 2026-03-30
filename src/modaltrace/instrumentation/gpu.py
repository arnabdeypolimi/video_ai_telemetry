"""GPU hardware monitoring via NVML.

Polls GPU metrics in a daemon thread and exposes them as OTel ObservableGauge
callbacks. Gracefully degrades if pynvml is unavailable or no NVIDIA GPU.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from typing import Any

from opentelemetry.metrics import Observation

from modaltrace.conventions.attributes import GPUAttributes
from modaltrace.conventions.namespaces import NAMESPACE as _NS

logger = logging.getLogger(f"{_NS}.gpu")


@dataclass
class GPUReading:
    """Snapshot of GPU metrics for a single device."""

    device_index: int = 0
    device_name: str = ""
    utilization_pct: float = 0.0
    memory_utilization_pct: float = 0.0
    memory_used_mb: float = 0.0
    memory_free_mb: float = 0.0
    memory_total_mb: float = 0.0
    temperature_c: float = 0.0
    power_w: float = 0.0


class GPUMonitor:
    """Polls NVML for GPU metrics and caches them for OTel gauge callbacks."""

    def __init__(
        self,
        poll_interval_s: float = 1.0,
        device_indices: list[int] | None = None,
    ) -> None:
        self._poll_interval_s = poll_interval_s
        self._device_indices = device_indices
        self._readings: list[GPUReading] = []
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._nvml_available = False
        self._handles: list[Any] = []

    def start(self) -> bool:
        """Initialize NVML and start polling. Returns False if unavailable."""
        try:
            import pynvml

            pynvml.nvmlInit()
            self._nvml_available = True
        except (ImportError, Exception) as exc:
            logger.debug("GPU monitoring unavailable: %s", exc)
            return False

        try:
            device_count = pynvml.nvmlDeviceGetCount()
        except Exception:
            logger.debug("Failed to get GPU device count")
            return False

        indices = self._device_indices or list(range(device_count))
        handles = []
        for idx in indices:
            try:
                handle = pynvml.nvmlDeviceGetHandleByIndex(idx)
                handles.append((idx, handle))
            except Exception:
                logger.debug("Failed to get handle for GPU %d", idx)

        if not handles:
            return False

        with self._lock:
            self._handles = handles

        self._thread = threading.Thread(target=self._poll_loop, daemon=True, name=f"{_NS}-gpu")
        self._thread.start()
        return True

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=5.0)
        if self._nvml_available:
            try:
                import pynvml

                pynvml.nvmlShutdown()
            except Exception:
                pass

    def get_readings(self) -> list[GPUReading]:
        with self._lock:
            return list(self._readings)

    def _poll_loop(self) -> None:
        while not self._stop.wait(timeout=self._poll_interval_s):
            self._poll()

    def _poll(self) -> None:
        import pynvml

        # Copy handles under lock to avoid race with start()
        with self._lock:
            handles = list(self._handles)

        readings = []
        for idx, handle in handles:
            reading = GPUReading(device_index=idx)

            try:
                reading.device_name = pynvml.nvmlDeviceGetName(handle)
            except Exception:
                pass

            try:
                util = pynvml.nvmlDeviceGetUtilizationRates(handle)
                reading.utilization_pct = float(util.gpu)
                reading.memory_utilization_pct = float(util.memory)
            except Exception:
                pass

            try:
                mem = pynvml.nvmlDeviceGetMemoryInfo(handle)
                reading.memory_used_mb = mem.used / (1024 * 1024)
                reading.memory_free_mb = mem.free / (1024 * 1024)
                reading.memory_total_mb = mem.total / (1024 * 1024)
            except Exception:
                pass

            try:
                reading.temperature_c = float(
                    pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
                )
            except Exception:
                pass

            try:
                reading.power_w = pynvml.nvmlDeviceGetPowerUsage(handle) / 1000.0
            except Exception:
                pass

            readings.append(reading)

        with self._lock:
            self._readings = readings

    def register_gauges(self, meter: Any) -> None:
        """Register OTel ObservableGauge instruments with callbacks."""

        def _make_callback(attr_name: str):
            def callback(options):
                readings = self.get_readings()
                for r in readings:
                    attrs = {GPUAttributes.DEVICE_INDEX: r.device_index}
                    if r.device_name:
                        attrs[GPUAttributes.DEVICE_NAME] = r.device_name
                    yield Observation(getattr(r, attr_name), attrs)

            return callback

        gauge_map = {
            f"{_NS}.gpu.utilization": "utilization_pct",
            f"{_NS}.gpu.memory.utilization": "memory_utilization_pct",
            f"{_NS}.gpu.memory.used": "memory_used_mb",
            f"{_NS}.gpu.memory.free": "memory_free_mb",
            f"{_NS}.gpu.memory.total": "memory_total_mb",
            f"{_NS}.gpu.temperature": "temperature_c",
            f"{_NS}.gpu.power.draw": "power_w",
        }

        for metric_name, attr_name in gauge_map.items():
            meter.create_observable_gauge(
                name=metric_name,
                callbacks=[_make_callback(attr_name)],
            )
