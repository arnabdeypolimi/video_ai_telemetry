"""Tests for OTLP protobuf parsing."""

from opentelemetry.proto.common.v1 import common_pb2
from opentelemetry.proto.logs.v1 import logs_pb2
from opentelemetry.proto.metrics.v1 import metrics_pb2
from opentelemetry.proto.trace.v1 import trace_pb2

from modaltrace.dashboard.proto_parser import (
    _compute_histogram_percentiles,
    parse_logs_request,
    parse_metrics_request,
    parse_traces_request,
)


class TestTracesParsing:
    """Test traces protobuf parsing."""

    def test_parse_simple_trace(self):
        """Test parsing a simple trace."""
        # Create a trace with one span
        traces_data = trace_pb2.TracesData()
        resource_span = traces_data.resource_spans.add()

        # Add resource attributes
        resource_span.resource.attributes.add(
            key="service.name", value=common_pb2.AnyValue(string_value="test-service")
        )

        # Add span
        scope_span = resource_span.scope_spans.add()
        span = scope_span.spans.add()
        span.trace_id = b"trace123456789ab"
        span.span_id = b"span12345678"
        span.name = "test_span"
        span.start_time_unix_nano = 1000000000  # 1 second in nanos
        span.end_time_unix_nano = 2000000000  # 2 seconds in nanos
        span.status.code = 1  # OK

        # Parse the protobuf
        body = traces_data.SerializeToString()
        spans = parse_traces_request(body)

        assert len(spans) == 1
        span_dict = spans[0]
        assert span_dict["name"] == "test_span"
        assert span_dict["service_name"] == "test-service"
        assert span_dict["status"] == "OK"
        assert span_dict["duration_ms"] == 1000

    def test_parse_trace_with_attributes(self):
        """Test parsing span with attributes."""
        traces_data = trace_pb2.TracesData()
        resource_span = traces_data.resource_spans.add()
        resource_span.resource.attributes.add(
            key="service.name", value=common_pb2.AnyValue(string_value="test")
        )

        scope_span = resource_span.scope_spans.add()
        span = scope_span.spans.add()
        span.trace_id = b"trace123456789ab"
        span.span_id = b"span12345678"
        span.name = "test_span"
        span.start_time_unix_nano = 1000000000
        span.end_time_unix_nano = 2000000000

        # Add attributes
        span.attributes.add(
            key="modaltrace.pipeline.frame.sequence_number",
            value=common_pb2.AnyValue(int_value=42),
        )
        span.attributes.add(
            key="custom.key", value=common_pb2.AnyValue(string_value="custom_value")
        )

        body = traces_data.SerializeToString()
        spans = parse_traces_request(body)

        assert len(spans) == 1
        attrs = spans[0]["attributes"]
        assert attrs["modaltrace.pipeline.frame.sequence_number"] == 42
        assert attrs["custom.key"] == "custom_value"

    def test_parse_trace_with_error_status(self):
        """Test parsing span with error status."""
        traces_data = trace_pb2.TracesData()
        resource_span = traces_data.resource_spans.add()
        resource_span.resource.attributes.add(
            key="service.name", value=common_pb2.AnyValue(string_value="test")
        )

        scope_span = resource_span.scope_spans.add()
        span = scope_span.spans.add()
        span.trace_id = b"trace123456789ab"
        span.span_id = b"span12345678"
        span.name = "failed_span"
        span.start_time_unix_nano = 1000000000
        span.end_time_unix_nano = 2000000000
        span.status.code = 2  # ERROR

        body = traces_data.SerializeToString()
        spans = parse_traces_request(body)

        assert spans[0]["status"] == "ERROR"

    def test_parse_multiple_spans(self):
        """Test parsing multiple spans."""
        traces_data = trace_pb2.TracesData()
        resource_span = traces_data.resource_spans.add()
        resource_span.resource.attributes.add(
            key="service.name", value=common_pb2.AnyValue(string_value="test")
        )

        scope_span = resource_span.scope_spans.add()
        for i in range(5):
            span = scope_span.spans.add()
            span.trace_id = f"trace{i}".encode().ljust(16, b"0")
            span.span_id = f"span{i}".encode().ljust(8, b"0")
            span.name = f"span_{i}"
            span.start_time_unix_nano = 1000000000 + i * 1000000000
            span.end_time_unix_nano = 2000000000 + i * 1000000000

        body = traces_data.SerializeToString()
        spans = parse_traces_request(body)

        assert len(spans) == 5
        for i, span in enumerate(spans):
            assert span["name"] == f"span_{i}"


class TestMetricsParsing:
    """Test metrics protobuf parsing."""

    def test_parse_gauge_metric(self):
        """Test parsing a gauge metric."""
        metrics_data = metrics_pb2.MetricsData()
        resource_metric = metrics_data.resource_metrics.add()
        scope_metric = resource_metric.scope_metrics.add()
        metric = scope_metric.metrics.add()

        metric.name = "modaltrace.gpu.utilization"
        gauge = metric.gauge
        data_point = gauge.data_points.add()
        data_point.time_unix_nano = 1000000000
        data_point.as_double = 0.75

        body = metrics_data.SerializeToString()
        points = parse_metrics_request(body)

        assert len(points) == 1
        point = points[0]
        assert point["name"] == "modaltrace.gpu.utilization"
        assert point["value"] == 0.75

    def test_parse_gauge_with_attributes(self):
        """Test parsing gauge metric with attributes."""
        metrics_data = metrics_pb2.MetricsData()
        resource_metric = metrics_data.resource_metrics.add()
        scope_metric = resource_metric.scope_metrics.add()
        metric = scope_metric.metrics.add()

        metric.name = "modaltrace.gpu.utilization"
        gauge = metric.gauge
        data_point = gauge.data_points.add()
        data_point.time_unix_nano = 1000000000
        data_point.as_double = 0.75

        # Add attributes
        data_point.attributes.add(
            key="modaltrace.gpu.device_index",
            value=common_pb2.AnyValue(int_value=0),
        )

        body = metrics_data.SerializeToString()
        points = parse_metrics_request(body)

        assert len(points) == 1
        point = points[0]
        assert point["attributes"]["modaltrace.gpu.device_index"] == 0

    def test_parse_histogram_metric(self):
        """Test parsing a histogram metric with percentiles."""
        metrics_data = metrics_pb2.MetricsData()
        resource_metric = metrics_data.resource_metrics.add()
        scope_metric = resource_metric.scope_metrics.add()
        metric = scope_metric.metrics.add()

        metric.name = "modaltrace.pipeline.stage.duration"
        histogram = metric.histogram
        data_point = histogram.data_points.add()
        data_point.time_unix_nano = 1000000000
        data_point.sum = 4500.0
        data_point.count = 100

        # Add bucket boundaries and counts
        # Boundaries: [1, 5, 10, 50, 100]
        data_point.explicit_bounds.extend([1.0, 5.0, 10.0, 50.0, 100.0])
        # Counts: [10, 20, 30, 25, 10, 5] (last bucket for values > max boundary)
        data_point.bucket_counts.extend([10, 20, 30, 25, 10, 5])

        body = metrics_data.SerializeToString()
        points = parse_metrics_request(body)

        assert len(points) == 1
        point = points[0]
        assert point["name"] == "modaltrace.pipeline.stage.duration"
        assert "percentiles" in point
        assert "p50" in point["percentiles"]
        assert "p95" in point["percentiles"]
        assert "p99" in point["percentiles"]

    def test_parse_histogram_percentiles(self):
        """Test histogram percentile computation."""
        bounds = [10.0, 20.0, 30.0, 40.0, 50.0]
        counts = [5, 10, 30, 35, 15, 5]

        percentiles = _compute_histogram_percentiles(bounds, counts)

        assert "p50" in percentiles
        assert "p95" in percentiles
        assert "p99" in percentiles

        # Percentiles should be within the bounds
        assert percentiles["p50"] >= bounds[0]
        assert percentiles["p95"] >= bounds[0]
        assert percentiles["p99"] >= bounds[0]

    def test_parse_counter_metric(self):
        """Test parsing a counter metric."""
        metrics_data = metrics_pb2.MetricsData()
        resource_metric = metrics_data.resource_metrics.add()
        scope_metric = resource_metric.scope_metrics.add()
        metric = scope_metric.metrics.add()

        metric.name = "modaltrace.frames.dropped"
        sum_metric = metric.sum
        data_point = sum_metric.data_points.add()
        data_point.time_unix_nano = 1000000000
        data_point.as_int = 42

        body = metrics_data.SerializeToString()
        points = parse_metrics_request(body)

        assert len(points) == 1
        point = points[0]
        assert point["name"] == "modaltrace.frames.dropped"
        assert point["value"] == 42

    def test_parse_multiple_metrics(self):
        """Test parsing multiple metrics."""
        metrics_data = metrics_pb2.MetricsData()
        resource_metric = metrics_data.resource_metrics.add()
        scope_metric = resource_metric.scope_metrics.add()

        # Add gauge metric
        gauge_metric = scope_metric.metrics.add()
        gauge_metric.name = "test.gauge"
        gauge = gauge_metric.gauge
        dp1 = gauge.data_points.add()
        dp1.time_unix_nano = 1000000000
        dp1.as_double = 0.5

        # Add counter metric
        counter_metric = scope_metric.metrics.add()
        counter_metric.name = "test.counter"
        counter = counter_metric.sum
        dp2 = counter.data_points.add()
        dp2.time_unix_nano = 1000000000
        dp2.as_int = 100

        body = metrics_data.SerializeToString()
        points = parse_metrics_request(body)

        assert len(points) == 2
        names = {p["name"] for p in points}
        assert "test.gauge" in names
        assert "test.counter" in names


class TestLogsParsing:
    """Test logs protobuf parsing."""

    def test_parse_simple_log(self):
        """Test parsing a simple log record."""
        logs_data = logs_pb2.LogsData()
        resource_log = logs_data.resource_logs.add()
        scope_log = resource_log.scope_logs.add()
        log_record = scope_log.log_records.add()

        log_record.time_unix_nano = 1000000000
        log_record.severity_number = 9  # INFO (OTLP: 9-12)
        log_record.body.string_value = "Test log message"

        body = logs_data.SerializeToString()
        records = parse_logs_request(body)

        assert len(records) == 1
        record = records[0]
        assert record["body"] == "Test log message"
        assert record["severity"] == "INFO"

    def test_parse_log_with_trace_context(self):
        """Test parsing log with trace context."""
        logs_data = logs_pb2.LogsData()
        resource_log = logs_data.resource_logs.add()
        scope_log = resource_log.scope_logs.add()
        log_record = scope_log.log_records.add()

        log_record.time_unix_nano = 1000000000
        log_record.severity_number = 4  # INFO
        log_record.body.string_value = "Test log"
        log_record.trace_id = b"trace123456789ab"
        log_record.span_id = b"span12345678"

        body = logs_data.SerializeToString()
        records = parse_logs_request(body)

        assert len(records) == 1
        record = records[0]
        assert record["trace_id"] is not None
        assert record["span_id"] is not None

    def test_parse_log_with_attributes(self):
        """Test parsing log with attributes."""
        logs_data = logs_pb2.LogsData()
        resource_log = logs_data.resource_logs.add()
        scope_log = resource_log.scope_logs.add()
        log_record = scope_log.log_records.add()

        log_record.time_unix_nano = 1000000000
        log_record.severity_number = 8  # ERROR
        log_record.body.string_value = "Error occurred"

        # Add attributes
        log_record.attributes.add(
            key="error.type", value=common_pb2.AnyValue(string_value="ValueError")
        )
        log_record.attributes.add(key="error.code", value=common_pb2.AnyValue(int_value=500))

        body = logs_data.SerializeToString()
        records = parse_logs_request(body)

        assert len(records) == 1
        record = records[0]
        assert record["attributes"]["error.type"] == "ValueError"
        assert record["attributes"]["error.code"] == 500

    def test_parse_log_severity_levels(self):
        """Test parsing logs with different severity levels."""
        severity_levels = [
            (9, "INFO"),  # OTLP INFO  = 9-12
            (13, "WARN"),  # OTLP WARN  = 13-16
            (17, "ERROR"),  # OTLP ERROR = 17-20
            (21, "FATAL"),  # OTLP FATAL = 21-24
        ]

        for severity_num, severity_name in severity_levels:
            logs_data = logs_pb2.LogsData()
            resource_log = logs_data.resource_logs.add()
            scope_log = resource_log.scope_logs.add()
            log_record = scope_log.log_records.add()

            log_record.time_unix_nano = 1000000000
            log_record.severity_number = severity_num
            log_record.body.string_value = f"{severity_name} message"

            body = logs_data.SerializeToString()
            records = parse_logs_request(body)

            assert records[0]["severity"] == severity_name

    def test_parse_multiple_logs(self):
        """Test parsing multiple log records."""
        logs_data = logs_pb2.LogsData()
        resource_log = logs_data.resource_logs.add()
        scope_log = resource_log.scope_logs.add()

        for i in range(5):
            log_record = scope_log.log_records.add()
            log_record.time_unix_nano = 1000000000 + i * 1000000000
            log_record.severity_number = 4  # INFO
            log_record.body.string_value = f"Message {i}"

        body = logs_data.SerializeToString()
        records = parse_logs_request(body)

        assert len(records) == 5
        for i, record in enumerate(records):
            assert f"Message {i}" in record["body"]


class TestParsingEdgeCases:
    """Test edge cases in parsing."""

    def test_parse_empty_traces(self):
        """Test parsing empty traces."""
        traces_data = trace_pb2.TracesData()
        body = traces_data.SerializeToString()
        spans = parse_traces_request(body)
        assert spans == []

    def test_parse_empty_metrics(self):
        """Test parsing empty metrics."""
        metrics_data = metrics_pb2.MetricsData()
        body = metrics_data.SerializeToString()
        points = parse_metrics_request(body)
        assert points == []

    def test_parse_empty_logs(self):
        """Test parsing empty logs."""
        logs_data = logs_pb2.LogsData()
        body = logs_data.SerializeToString()
        records = parse_logs_request(body)
        assert records == []

    def test_parse_span_without_service_name(self):
        """Test parsing span when service.name is not set."""
        traces_data = trace_pb2.TracesData()
        resource_span = traces_data.resource_spans.add()
        # Don't set service name

        scope_span = resource_span.scope_spans.add()
        span = scope_span.spans.add()
        span.trace_id = b"trace123456789ab"
        span.span_id = b"span12345678"
        span.name = "test_span"
        span.start_time_unix_nano = 1000000000
        span.end_time_unix_nano = 2000000000

        body = traces_data.SerializeToString()
        spans = parse_traces_request(body)

        assert len(spans) == 1
        assert spans[0]["service_name"] == "unknown"

    def test_parse_histogram_with_zero_count(self):
        """Test histogram percentiles with zero count."""
        bounds = [10.0, 20.0, 30.0]
        counts = [0, 0, 0, 0]

        percentiles = _compute_histogram_percentiles(bounds, counts)

        assert percentiles["p50"] == 0.0
        assert percentiles["p95"] == 0.0
        assert percentiles["p99"] == 0.0
