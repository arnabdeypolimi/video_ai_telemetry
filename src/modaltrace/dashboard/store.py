"""Thread-safe in-memory ring buffer store for telemetry data."""

import threading
from collections import deque
from typing import Any


class TelemetryStore:
    """
    Thread-safe store for spans, metrics, and logs using ring buffers (deques).

    Maintains three separate circular buffers:
    - spans: recent trace spans (max 2000)
    - metric_points: individual metric data points (max 10000)
    - logs: log records (max 5000)
    """

    def __init__(self):
        """Initialize ring buffers and lock."""
        self._lock = threading.Lock()
        self._spans = deque(maxlen=2000)
        self._metric_points = deque(maxlen=10000)
        self._logs = deque(maxlen=5000)

    def add_span(self, span: dict) -> None:
        """Add a span to the store."""
        with self._lock:
            self._spans.append(span)

    def add_metric_point(self, metric_point: dict) -> None:
        """Add a metric point to the store."""
        with self._lock:
            self._metric_points.append(metric_point)

    def add_log(self, log_record: dict) -> None:
        """Add a log record to the store."""
        with self._lock:
            self._logs.append(log_record)

    def get_spans(self, since_ms: int | None = None, limit: int = 50) -> list[dict]:
        """Get recent spans, optionally filtered by timestamp and limited."""
        with self._lock:
            spans = list(self._spans)

        # Filter by timestamp if provided
        if since_ms is not None:
            spans = [s for s in spans if s.get("start_time_ms", 0) >= since_ms]

        # Return newest first, limited to count
        return sorted(spans, key=lambda s: s.get("start_time_ms", 0), reverse=True)[:limit]

    def get_metric_series(
        self, name: str, since_ms: int | None = None
    ) -> list[dict]:
        """Get metric time series for a given metric name."""
        with self._lock:
            points = list(self._metric_points)

        # Filter by metric name and timestamp
        series = [p for p in points if p.get("name") == name]
        if since_ms is not None:
            series = [p for p in series if p.get("timestamp_ms", 0) >= since_ms]

        # Return sorted by timestamp
        return sorted(series, key=lambda p: p.get("timestamp_ms", 0))

    def get_latest_gpu(self) -> dict[str, Any]:
        """Get latest GPU readings, grouped by device_index."""
        with self._lock:
            points = list(self._metric_points)

        # Filter to GPU metrics only
        gpu_points = [
            p for p in points
            if p.get("name", "").startswith("modaltrace.gpu.")
        ]

        # Group by device_index and keep latest per metric per device
        gpu_data: dict[int, dict[str, Any]] = {}
        for point in gpu_points:
            device_id = point.get("attributes", {}).get("modaltrace.gpu.device_index", 0)
            metric_name = point.get("name", "")

            if device_id not in gpu_data:
                gpu_data[device_id] = {"device_index": device_id}

            # Store latest value for each metric
            gpu_data[device_id][metric_name] = point.get("value")

            # Capture device name from attributes (present on all GPU metrics)
            device_name = point.get("attributes", {}).get("modaltrace.gpu.device_name")
            if device_name and "device_name" not in gpu_data[device_id]:
                gpu_data[device_id]["device_name"] = device_name

        return gpu_data

    def get_logs(
        self, since_ms: int | None = None, level: str | None = None, limit: int = 100
    ) -> list[dict]:
        """Get log records, optionally filtered by timestamp, severity level, and limited."""
        with self._lock:
            logs = list(self._logs)

        # Filter by timestamp if provided
        if since_ms is not None:
            logs = [log for log in logs if log.get("timestamp_ms", 0) >= since_ms]

        # Filter by severity level if provided
        if level is not None:
            logs = [log for log in logs if log.get("severity") == level]

        # Return newest first, limited to count
        return sorted(logs, key=lambda log: log.get("timestamp_ms", 0), reverse=True)[:limit]
