"""Tests for dashboard API endpoints."""

import pytest
from fastapi.testclient import TestClient

from modaltrace.dashboard.server import app, store


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def clear_store():
    """Clear the store before each test."""
    store.clear()
    yield
    store.clear()


class TestSpansEndpoint:
    """Test /api/spans endpoint."""

    def test_get_empty_spans(self, client):
        """Test getting spans from empty store."""
        response = client.get("/api/spans")
        assert response.status_code == 200
        assert response.json() == []

    def test_get_spans_with_data(self, client):
        """Test getting spans with data in store."""
        # Add test data directly to store
        store.add_span(
            {
                "trace_id": "abc123",
                "span_id": "def456",
                "name": "test_span",
                "service_name": "test-service",
                "start_time_ms": 1000,
                "duration_ms": 50,
                "status": "OK",
                "attributes": {"key": "value"},
            }
        )

        response = client.get("/api/spans")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "test_span"

    def test_get_spans_with_limit(self, client):
        """Test limiting span results."""
        import time

        now = int(time.time() * 1000)

        # Add 10 spans
        for i in range(10):
            store.add_span(
                {
                    "trace_id": f"trace{i}",
                    "span_id": f"span{i}",
                    "name": f"span_{i}",
                    "service_name": "test",
                    "start_time_ms": now - i * 100,
                    "duration_ms": 10,
                    "status": "OK",
                    "attributes": {},
                }
            )

        response = client.get("/api/spans?limit=5")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 5

    def test_get_spans_with_since_ms(self, client):
        """Test filtering spans by timestamp."""
        import time

        now = int(time.time() * 1000)

        # Add spans with different timestamps
        for i in range(5):
            store.add_span(
                {
                    "trace_id": f"trace{i}",
                    "span_id": f"span{i}",
                    "name": f"span_{i}",
                    "service_name": "test",
                    "start_time_ms": now - (5 - i) * 100,
                    "duration_ms": 10,
                    "status": "OK",
                    "attributes": {},
                }
            )

        cutoff = now - 200
        response = client.get(f"/api/spans?since_ms={cutoff}")
        assert response.status_code == 200
        data = response.json()

        for span in data:
            assert span["start_time_ms"] >= cutoff


class TestMetricsEndpoint:
    """Test /api/metrics/{name} endpoint."""

    def test_get_metric_not_found(self, client):
        """Test getting non-existent metric."""
        response = client.get("/api/metrics/nonexistent.metric")
        assert response.status_code == 200
        assert response.json() == []

    def test_get_metric_with_data(self, client):
        """Test getting metric with data."""
        store.add_metric_point(
            {
                "name": "modaltrace.pipeline.stage.duration",
                "value": 45.5,
                "timestamp_ms": 1000,
                "attributes": {"modaltrace.pipeline.stage": "inference"},
                "percentiles": {"p50": 40, "p95": 45.5, "p99": 50},
            }
        )

        response = client.get("/api/metrics/modaltrace.pipeline.stage.duration")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "modaltrace.pipeline.stage.duration"

    def test_get_metric_name_conversion(self, client):
        """Test metric name conversion from double underscore to dot."""
        store.add_metric_point(
            {
                "name": "modaltrace.gpu.utilization",
                "value": 0.75,
                "timestamp_ms": 1000,
                "attributes": {},
            }
        )

        # Request with double underscore (URL encoding)
        response = client.get("/api/metrics/modaltrace__gpu__utilization")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "modaltrace.gpu.utilization"

    def test_get_metric_with_since_ms(self, client):
        """Test filtering metrics by timestamp."""
        import time

        now = int(time.time() * 1000)

        # Add multiple metrics
        for i in range(5):
            store.add_metric_point(
                {
                    "name": "test.metric",
                    "value": i * 10,
                    "timestamp_ms": now - (5 - i) * 100,
                    "attributes": {},
                }
            )

        cutoff = now - 300
        response = client.get(f"/api/metrics/test.metric?since_ms={cutoff}")
        assert response.status_code == 200
        data = response.json()

        for metric in data:
            assert metric["timestamp_ms"] >= cutoff

    def test_get_metric_with_percentiles(self, client):
        """Test metrics with percentile data."""
        store.add_metric_point(
            {
                "name": "modaltrace.pipeline.stage.duration",
                "value": 45.5,
                "timestamp_ms": 1000,
                "attributes": {"modaltrace.pipeline.stage": "inference"},
                "percentiles": {"p50": 40, "p95": 45.5, "p99": 50},
                "count": 100,
            }
        )

        response = client.get("/api/metrics/modaltrace.pipeline.stage.duration")
        assert response.status_code == 200
        data = response.json()
        assert "percentiles" in data[0]
        assert data[0]["percentiles"]["p95"] == 45.5


class TestGPUEndpoint:
    """Test /api/gpu endpoint."""

    def test_get_gpu_empty(self, client):
        """Test getting GPU data from empty store."""
        response = client.get("/api/gpu")
        assert response.status_code == 200
        assert response.json() == {}

    def test_get_gpu_single_device(self, client):
        """Test GPU data for single device."""
        store.add_metric_point(
            {
                "name": "modaltrace.gpu.utilization",
                "value": 0.75,
                "timestamp_ms": 1000,
                "attributes": {"modaltrace.gpu.device_index": 0},
            }
        )
        store.add_metric_point(
            {
                "name": "modaltrace.gpu.memory.used",
                "value": 8.5,
                "timestamp_ms": 1000,
                "attributes": {"modaltrace.gpu.device_index": 0},
            }
        )

        response = client.get("/api/gpu")
        assert response.status_code == 200
        data = response.json()
        assert "0" in data
        assert data["0"]["modaltrace.gpu.utilization"] == 0.75
        assert data["0"]["modaltrace.gpu.memory.used"] == 8.5

    def test_get_gpu_multiple_devices(self, client):
        """Test GPU data for multiple devices."""
        for device_id in [0, 1, 2]:
            store.add_metric_point(
                {
                    "name": "modaltrace.gpu.utilization",
                    "value": 0.5 + device_id * 0.1,
                    "timestamp_ms": 1000,
                    "attributes": {"modaltrace.gpu.device_index": device_id},
                }
            )
            store.add_metric_point(
                {
                    "name": "modaltrace.gpu.temperature",
                    "value": 60 + device_id * 5,
                    "timestamp_ms": 1000,
                    "attributes": {"modaltrace.gpu.device_index": device_id},
                }
            )

        response = client.get("/api/gpu")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        for device_id in [0, 1, 2]:
            assert str(device_id) in data

    def test_get_gpu_latest_values(self, client):
        """Test that latest values are returned."""
        device_id = 0
        # Add old value
        store.add_metric_point(
            {
                "name": "modaltrace.gpu.utilization",
                "value": 0.5,
                "timestamp_ms": 1000,
                "attributes": {"modaltrace.gpu.device_index": device_id},
            }
        )

        # Add newer value
        store.add_metric_point(
            {
                "name": "modaltrace.gpu.utilization",
                "value": 0.8,
                "timestamp_ms": 2000,
                "attributes": {"modaltrace.gpu.device_index": device_id},
            }
        )

        response = client.get("/api/gpu")
        data = response.json()
        # Should have the newest value
        assert data["0"]["modaltrace.gpu.utilization"] == 0.8


class TestLogsEndpoint:
    """Test /api/logs endpoint."""

    def test_get_empty_logs(self, client):
        """Test getting logs from empty store."""
        response = client.get("/api/logs")
        assert response.status_code == 200
        assert response.json() == []

    def test_get_logs_with_data(self, client):
        """Test getting logs with data."""
        store.add_log(
            {
                "timestamp_ms": 1000,
                "severity": "INFO",
                "body": "Test log message",
                "trace_id": "abc123",
                "span_id": "def456",
                "attributes": {"key": "value"},
            }
        )

        response = client.get("/api/logs")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["body"] == "Test log message"

    def test_get_logs_with_level_filter(self, client):
        """Test filtering logs by severity level."""
        import time

        now = int(time.time() * 1000)

        # Add logs with different severity levels
        for severity in ["ERROR", "WARN", "INFO", "DEBUG"]:
            store.add_log(
                {
                    "timestamp_ms": now,
                    "severity": severity,
                    "body": f"{severity} message",
                    "trace_id": None,
                    "span_id": None,
                    "attributes": {},
                }
            )

        # Get only ERROR logs
        response = client.get("/api/logs?level=ERROR")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["severity"] == "ERROR"

    def test_get_logs_with_limit(self, client):
        """Test limiting log results."""
        import time

        now = int(time.time() * 1000)

        # Add 20 logs
        for i in range(20):
            store.add_log(
                {
                    "timestamp_ms": now - i * 100,
                    "severity": "INFO",
                    "body": f"Message {i}",
                    "trace_id": None,
                    "span_id": None,
                    "attributes": {},
                }
            )

        response = client.get("/api/logs?limit=10")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 10

    def test_get_logs_with_since_ms(self, client):
        """Test filtering logs by timestamp."""
        import time

        now = int(time.time() * 1000)

        # Add logs with different timestamps
        for i in range(5):
            store.add_log(
                {
                    "timestamp_ms": now - (5 - i) * 100,
                    "severity": "INFO",
                    "body": f"Message {i}",
                    "trace_id": None,
                    "span_id": None,
                    "attributes": {},
                }
            )

        cutoff = now - 300
        response = client.get(f"/api/logs?since_ms={cutoff}")
        assert response.status_code == 200
        data = response.json()

        for log in data:
            assert log["timestamp_ms"] >= cutoff


class TestOTLPReceiverEndpoints:
    """Test OTLP receiver endpoints."""

    def test_post_traces_empty_body(self, client):
        """Test posting empty traces."""
        # This would normally be a protobuf message
        # For now, just test that endpoint exists
        response = client.post("/v1/traces", content=b"")
        assert response.status_code == 200

    def test_post_metrics_empty_body(self, client):
        """Test posting empty metrics."""
        response = client.post("/v1/metrics", content=b"")
        assert response.status_code == 200

    def test_post_logs_empty_body(self, client):
        """Test posting empty logs."""
        response = client.post("/v1/logs", content=b"")
        assert response.status_code == 200

    def test_receiver_endpoints_return_empty_dict(self, client):
        """Test that receiver endpoints return empty dict."""
        for endpoint in ["/v1/traces", "/v1/metrics", "/v1/logs"]:
            response = client.post(endpoint, content=b"")
            assert response.status_code == 200
            assert response.json() == {}


class TestStaticFileServing:
    """Test static file serving."""

    def test_root_path_exists(self, client):
        """Test that root path serves static files."""
        # The dashboard will mount static files at root
        # This test just verifies the app doesn't error
        response = client.get("/")
        # Will return 404 or HTML depending on if static files are mounted
        assert response.status_code in [200, 404]


class TestAPIDataStructures:
    """Test API response data structures."""

    def test_span_response_structure(self, client):
        """Test span response has expected structure."""
        store.add_span(
            {
                "trace_id": "abc123",
                "span_id": "def456",
                "name": "test_span",
                "service_name": "test-service",
                "start_time_ms": 1000,
                "duration_ms": 50,
                "status": "OK",
                "attributes": {"key": "value"},
            }
        )

        response = client.get("/api/spans")
        data = response.json()
        assert len(data) == 1
        span = data[0]

        # Check all expected fields
        assert "trace_id" in span
        assert "span_id" in span
        assert "name" in span
        assert "service_name" in span
        assert "start_time_ms" in span
        assert "duration_ms" in span
        assert "status" in span
        assert "attributes" in span

    def test_metric_response_structure(self, client):
        """Test metric response has expected structure."""
        store.add_metric_point(
            {
                "name": "test.metric",
                "value": 42.5,
                "timestamp_ms": 1000,
                "attributes": {"stage": "inference"},
                "percentiles": {"p50": 40, "p95": 42.5, "p99": 45},
            }
        )

        response = client.get("/api/metrics/test.metric")
        data = response.json()
        assert len(data) == 1
        metric = data[0]

        # Check all expected fields
        assert "name" in metric
        assert "value" in metric
        assert "timestamp_ms" in metric
        assert "attributes" in metric

    def test_log_response_structure(self, client):
        """Test log response has expected structure."""
        store.add_log(
            {
                "timestamp_ms": 1000,
                "severity": "INFO",
                "body": "Test message",
                "trace_id": "abc123",
                "span_id": "def456",
                "attributes": {"key": "value"},
            }
        )

        response = client.get("/api/logs")
        data = response.json()
        assert len(data) == 1
        log = data[0]

        # Check all expected fields
        assert "timestamp_ms" in log
        assert "severity" in log
        assert "body" in log
        assert "trace_id" in log
        assert "span_id" in log
        assert "attributes" in log
