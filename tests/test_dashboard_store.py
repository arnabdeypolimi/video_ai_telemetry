"""Tests for dashboard telemetry storage."""

import time

import pytest

from modaltrace.dashboard.store import TelemetryStore


@pytest.fixture
def store():
    """Create a fresh TelemetryStore for each test."""
    return TelemetryStore()


class TestTelemetryStoreSpans:
    """Test span storage and retrieval."""

    def test_add_span(self, store):
        """Test adding a single span."""
        span = {
            "trace_id": "abc123",
            "span_id": "def456",
            "name": "test_span",
            "service_name": "test-service",
            "start_time_ms": 1000,
            "end_time_ms": 1050,
            "duration_ms": 50,
            "status": "OK",
            "attributes": {"key": "value"},
        }
        store.add_span(span)
        spans = store.get_spans()
        assert len(spans) == 1
        assert spans[0]["name"] == "test_span"

    def test_get_spans_newest_first(self, store):
        """Test spans are returned newest first."""
        now = int(time.time() * 1000)
        for i in range(3):
            store.add_span({
                "trace_id": f"trace{i}",
                "span_id": f"span{i}",
                "name": f"span_{i}",
                "service_name": "test",
                "start_time_ms": now - (3 - i) * 100,  # Earlier times first
                "duration_ms": 10,
                "status": "OK",
                "attributes": {},
            })

        spans = store.get_spans()
        # Should be ordered newest (highest timestamp) first
        assert spans[0]["start_time_ms"] > spans[1]["start_time_ms"]
        assert spans[1]["start_time_ms"] > spans[2]["start_time_ms"]

    def test_get_spans_with_since_ms(self, store):
        """Test filtering spans by timestamp."""
        now = int(time.time() * 1000)
        for i in range(5):
            store.add_span({
                "trace_id": f"trace{i}",
                "span_id": f"span{i}",
                "name": f"span_{i}",
                "service_name": "test",
                "start_time_ms": now - (5 - i) * 100,
                "duration_ms": 10,
                "status": "OK",
                "attributes": {},
            })

        # Get spans after time T (only newer spans)
        cutoff = now - 300
        spans = store.get_spans(since_ms=cutoff)

        # Should only get spans with start_time_ms >= cutoff
        for span in spans:
            assert span["start_time_ms"] >= cutoff

    def test_get_spans_with_limit(self, store):
        """Test limiting span count."""
        now = int(time.time() * 1000)
        for i in range(100):
            store.add_span({
                "trace_id": f"trace{i}",
                "span_id": f"span{i}",
                "name": f"span_{i}",
                "service_name": "test",
                "start_time_ms": now - i * 10,
                "duration_ms": 5,
                "status": "OK",
                "attributes": {},
            })

        spans = store.get_spans(limit=50)
        assert len(spans) == 50

    def test_span_ring_buffer_max_capacity(self, store):
        """Test that span buffer doesn't exceed max capacity."""
        now = int(time.time() * 1000)
        # Add more than max capacity (2000)
        for i in range(2500):
            store.add_span({
                "trace_id": f"trace{i}",
                "span_id": f"span{i}",
                "name": f"span_{i}",
                "service_name": "test",
                "start_time_ms": now - i * 10,
                "duration_ms": 5,
                "status": "OK",
                "attributes": {},
            })

        # Buffer should only keep latest 2000
        spans = store.get_spans(limit=3000)  # Request more than available
        assert len(spans) <= 2000


class TestTelemetryStoreMetrics:
    """Test metric storage and retrieval."""

    def test_add_metric_point(self, store):
        """Test adding a metric point."""
        metric = {
            "name": "modaltrace.pipeline.stage.duration",
            "value": 45.5,
            "timestamp_ms": 1000,
            "attributes": {"modaltrace.pipeline.stage": "inference"},
            "percentiles": {"p50": 40, "p95": 45.5, "p99": 50},
        }
        store.add_metric_point(metric)
        metrics = store.get_metric_series("modaltrace.pipeline.stage.duration")
        assert len(metrics) == 1
        assert metrics[0]["value"] == 45.5

    def test_get_metric_series_by_name(self, store):
        """Test retrieving metrics by name."""
        now = int(time.time() * 1000)

        # Add metrics with different names
        for i in range(3):
            store.add_metric_point({
                "name": "modaltrace.pipeline.stage.duration",
                "value": 40 + i * 5,
                "timestamp_ms": now - (3 - i) * 100,
                "attributes": {"modaltrace.pipeline.stage": "inference"},
                "percentiles": {"p50": 40, "p95": 45, "p99": 50},
            })

        for i in range(2):
            store.add_metric_point({
                "name": "modaltrace.frames.dropped",
                "value": i,
                "timestamp_ms": now - i * 100,
                "attributes": {},
            })

        # Get only pipeline metrics
        pipeline_metrics = store.get_metric_series("modaltrace.pipeline.stage.duration")
        assert len(pipeline_metrics) == 3
        assert all(m["name"] == "modaltrace.pipeline.stage.duration" for m in pipeline_metrics)

    def test_get_metric_series_sorted_by_timestamp(self, store):
        """Test metrics are sorted by timestamp."""
        now = int(time.time() * 1000)
        for i in range(5):
            store.add_metric_point({
                "name": "test.metric",
                "value": i * 10,
                "timestamp_ms": now - (5 - i) * 100,
                "attributes": {},
            })

        metrics = store.get_metric_series("test.metric")
        # Should be sorted oldest first
        for i in range(len(metrics) - 1):
            assert metrics[i]["timestamp_ms"] <= metrics[i + 1]["timestamp_ms"]

    def test_get_metric_series_with_since_ms(self, store):
        """Test filtering metrics by timestamp."""
        now = int(time.time() * 1000)
        for i in range(10):
            store.add_metric_point({
                "name": "test.metric",
                "value": i,
                "timestamp_ms": now - (10 - i) * 100,
                "attributes": {},
            })

        cutoff = now - 500
        metrics = store.get_metric_series("test.metric", since_ms=cutoff)

        for metric in metrics:
            assert metric["timestamp_ms"] >= cutoff

    def test_metric_ring_buffer_max_capacity(self, store):
        """Test that metric buffer doesn't exceed max capacity."""
        now = int(time.time() * 1000)
        # Add more than max capacity (10000)
        for i in range(12000):
            store.add_metric_point({
                "name": f"test.metric.{i % 10}",
                "value": i % 100,
                "timestamp_ms": now - i,
                "attributes": {},
            })

        # Total metrics should not exceed 10000
        total_metrics = 0
        for j in range(10):
            metrics = store.get_metric_series(f"test.metric.{j}")
            total_metrics += len(metrics)

        assert total_metrics <= 10000


class TestTelemetryStoreGPU:
    """Test GPU metric aggregation."""

    def test_get_latest_gpu_single_device(self, store):
        """Test getting latest GPU metrics for single device."""
        store.add_metric_point({
            "name": "modaltrace.gpu.utilization",
            "value": 0.75,
            "timestamp_ms": 1000,
            "attributes": {"modaltrace.gpu.device_index": 0},
        })
        store.add_metric_point({
            "name": "modaltrace.gpu.memory.used",
            "value": 8.5,
            "timestamp_ms": 1000,
            "attributes": {"modaltrace.gpu.device_index": 0},
        })

        gpu_data = store.get_latest_gpu()
        assert 0 in gpu_data
        assert gpu_data[0]["modaltrace.gpu.utilization"] == 0.75
        assert gpu_data[0]["modaltrace.gpu.memory.used"] == 8.5

    def test_get_latest_gpu_multiple_devices(self, store):
        """Test GPU data for multiple devices."""
        for device_id in [0, 1, 2]:
            store.add_metric_point({
                "name": "modaltrace.gpu.utilization",
                "value": 0.5 + device_id * 0.1,
                "timestamp_ms": 1000,
                "attributes": {"modaltrace.gpu.device_index": device_id},
            })

        gpu_data = store.get_latest_gpu()
        assert len(gpu_data) == 3
        assert all(device_id in gpu_data for device_id in [0, 1, 2])

    def test_get_latest_gpu_ignores_non_gpu_metrics(self, store):
        """Test that non-GPU metrics are excluded."""
        store.add_metric_point({
            "name": "modaltrace.gpu.utilization",
            "value": 0.75,
            "timestamp_ms": 1000,
            "attributes": {"modaltrace.gpu.device_index": 0},
        })
        store.add_metric_point({
            "name": "modaltrace.frames.dropped",
            "value": 1,
            "timestamp_ms": 1000,
            "attributes": {},
        })

        gpu_data = store.get_latest_gpu()
        assert 0 in gpu_data
        assert "modaltrace.frames.dropped" not in gpu_data[0]


class TestTelemetryStoreLogs:
    """Test log storage and retrieval."""

    def test_add_log(self, store):
        """Test adding a log record."""
        log = {
            "timestamp_ms": 1000,
            "severity": "INFO",
            "body": "Test message",
            "trace_id": "abc123",
            "span_id": "def456",
            "attributes": {"key": "value"},
        }
        store.add_log(log)
        logs = store.get_logs()
        assert len(logs) == 1
        assert logs[0]["body"] == "Test message"

    def test_get_logs_newest_first(self, store):
        """Test logs are returned newest first."""
        now = int(time.time() * 1000)
        for i in range(3):
            store.add_log({
                "timestamp_ms": now - (3 - i) * 100,
                "severity": "INFO",
                "body": f"Message {i}",
                "trace_id": None,
                "span_id": None,
                "attributes": {},
            })

        logs = store.get_logs()
        # Should be ordered newest first
        assert logs[0]["timestamp_ms"] > logs[1]["timestamp_ms"]
        assert logs[1]["timestamp_ms"] > logs[2]["timestamp_ms"]

    def test_get_logs_with_severity_filter(self, store):
        """Test filtering logs by severity."""
        now = int(time.time() * 1000)
        severities = ["ERROR", "WARN", "INFO", "DEBUG"]
        for i, severity in enumerate(severities):
            store.add_log({
                "timestamp_ms": now - i * 100,
                "severity": severity,
                "body": f"{severity} message",
                "trace_id": None,
                "span_id": None,
                "attributes": {},
            })

        # Get only ERROR logs
        error_logs = store.get_logs(level="ERROR")
        assert len(error_logs) == 1
        assert error_logs[0]["severity"] == "ERROR"

    def test_get_logs_with_since_ms(self, store):
        """Test filtering logs by timestamp."""
        now = int(time.time() * 1000)
        for i in range(5):
            store.add_log({
                "timestamp_ms": now - (5 - i) * 100,
                "severity": "INFO",
                "body": f"Message {i}",
                "trace_id": None,
                "span_id": None,
                "attributes": {},
            })

        cutoff = now - 300
        logs = store.get_logs(since_ms=cutoff)

        for log in logs:
            assert log["timestamp_ms"] >= cutoff

    def test_get_logs_with_limit(self, store):
        """Test limiting log count."""
        now = int(time.time() * 1000)
        for i in range(150):
            store.add_log({
                "timestamp_ms": now - i * 10,
                "severity": "INFO",
                "body": f"Message {i}",
                "trace_id": None,
                "span_id": None,
                "attributes": {},
            })

        logs = store.get_logs(limit=100)
        assert len(logs) == 100

    def test_log_ring_buffer_max_capacity(self, store):
        """Test that log buffer doesn't exceed max capacity."""
        now = int(time.time() * 1000)
        # Add more than max capacity (5000)
        for i in range(6000):
            store.add_log({
                "timestamp_ms": now - i,
                "severity": "INFO",
                "body": f"Message {i}",
                "trace_id": None,
                "span_id": None,
                "attributes": {},
            })

        logs = store.get_logs(limit=10000)  # Request more than available
        assert len(logs) <= 5000


class TestTelemetryStoreThreadSafety:
    """Test thread-safe operations."""

    def test_concurrent_span_adds(self, store):
        """Test adding spans from multiple threads."""
        import threading

        def add_spans(start_idx, count):
            for i in range(start_idx, start_idx + count):
                store.add_span({
                    "trace_id": f"trace{i}",
                    "span_id": f"span{i}",
                    "name": f"span_{i}",
                    "service_name": "test",
                    "start_time_ms": 1000 + i,
                    "duration_ms": 10,
                    "status": "OK",
                    "attributes": {},
                })

        threads = []
        for i in range(4):
            t = threading.Thread(target=add_spans, args=(i * 250, 250))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        spans = store.get_spans(limit=1000)
        assert len(spans) == 1000

    def test_concurrent_reads_and_writes(self, store):
        """Test reading while writing."""
        import threading

        results = []

        def add_data():
            for i in range(100):
                store.add_span({
                    "trace_id": f"trace{i}",
                    "span_id": f"span{i}",
                    "name": f"span_{i}",
                    "service_name": "test",
                    "start_time_ms": 1000 + i,
                    "duration_ms": 10,
                    "status": "OK",
                    "attributes": {},
                })
                store.add_metric_point({
                    "name": "test.metric",
                    "value": i,
                    "timestamp_ms": 1000 + i,
                    "attributes": {},
                })

        def read_data():
            for _ in range(50):
                spans = store.get_spans()
                metrics = store.get_metric_series("test.metric")
                results.append(len(spans) + len(metrics))

        writer = threading.Thread(target=add_data)
        readers = [threading.Thread(target=read_data) for _ in range(3)]

        writer.start()
        for reader in readers:
            reader.start()

        writer.join()
        for reader in readers:
            reader.join()

        # All reads should succeed without errors
        assert len(results) == 150


class TestTelemetryStoreEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_store_queries(self, store):
        """Test querying empty store."""
        assert store.get_spans() == []
        assert store.get_metric_series("test.metric") == []
        assert store.get_logs() == []
        assert store.get_latest_gpu() == {}

    def test_none_values_in_attributes(self, store):
        """Test handling None values."""
        span = {
            "trace_id": "abc123",
            "span_id": "def456",
            "name": "test",
            "service_name": None,
            "start_time_ms": 1000,
            "duration_ms": 10,
            "status": "OK",
            "attributes": {"key": None},
        }
        store.add_span(span)
        spans = store.get_spans()
        assert spans[0]["service_name"] is None

    def test_very_large_attribute_values(self, store):
        """Test storing large attribute values."""
        span = {
            "trace_id": "abc123",
            "span_id": "def456",
            "name": "test",
            "service_name": "test",
            "start_time_ms": 1000,
            "duration_ms": 10,
            "status": "OK",
            "attributes": {"large_data": "x" * 10000},
        }
        store.add_span(span)
        spans = store.get_spans()
        assert len(spans[0]["attributes"]["large_data"]) == 10000

    def test_negative_timestamps(self, store):
        """Test handling negative timestamps (edge case)."""
        metric = {
            "name": "test.metric",
            "value": 1.0,
            "timestamp_ms": -1000,
            "attributes": {},
        }
        store.add_metric_point(metric)
        metrics = store.get_metric_series("test.metric")
        assert len(metrics) == 1
        assert metrics[0]["timestamp_ms"] == -1000
