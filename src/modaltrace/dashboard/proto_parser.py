"""Parse OTLP protobuf messages into plain Python dictionaries."""

import time
from typing import Any

from opentelemetry.proto.logs.v1 import logs_pb2
from opentelemetry.proto.metrics.v1 import metrics_pb2
from opentelemetry.proto.trace.v1 import trace_pb2


def _nanoseconds_to_milliseconds(ns: int) -> int:
    """Convert nanoseconds to milliseconds."""
    return ns // 1_000_000


def _extract_attributes(pb_attrs: Any) -> dict[str, Any]:
    """Extract attributes from protobuf KeyValue list or map."""
    result = {}

    # Handle both repeated KeyValue list and map format
    try:
        # Try treating it as an iterable of KeyValue objects
        for kv in pb_attrs:
            key = kv.key
            value = kv.value

            if value.HasField("string_value"):
                result[key] = value.string_value
            elif value.HasField("int_value"):
                result[key] = value.int_value
            elif value.HasField("double_value"):
                result[key] = value.double_value
            elif value.HasField("bool_value"):
                result[key] = value.bool_value
            elif value.HasField("array_value"):
                result[key] = f"[array: {len(value.array_value.values)} items]"
            else:
                result[key] = str(value)
    except (TypeError, AttributeError):
        # Fallback for dict-like access
        try:
            for key, value in pb_attrs.items():
                if value.HasField("string_value"):
                    result[key] = value.string_value
                elif value.HasField("int_value"):
                    result[key] = value.int_value
                elif value.HasField("double_value"):
                    result[key] = value.double_value
                elif value.HasField("bool_value"):
                    result[key] = value.bool_value
                else:
                    result[key] = str(value)
        except Exception:
            pass

    return result


def parse_traces_request(body: bytes) -> list[dict]:
    """
    Parse OTLP TracesData protobuf into list of span dicts.

    Returns:
        List of dicts with keys:
        - trace_id: hex string
        - span_id: hex string
        - parent_span_id: hex string (or None)
        - name: span name
        - service_name: from resource attributes
        - start_time_ms: milliseconds since epoch
        - end_time_ms: milliseconds since epoch
        - duration_ms: end - start
        - status: "UNSET", "OK", or "ERROR"
        - attributes: dict
    """
    traces_data = trace_pb2.TracesData()
    traces_data.ParseFromString(body)

    spans = []
    for resource_span in traces_data.resource_spans:
        # Get service name from resource attributes
        service_name = "unknown"
        resource_attrs = _extract_attributes(resource_span.resource.attributes)
        if "service.name" in resource_attrs:
            service_name = resource_attrs["service.name"]

        for scope_span in resource_span.scope_spans:
            for span in scope_span.spans:
                start_ms = _nanoseconds_to_milliseconds(span.start_time_unix_nano)
                end_ms = _nanoseconds_to_milliseconds(span.end_time_unix_nano)
                duration_ms = end_ms - start_ms

                # Map status code to string
                status_map = {
                    0: "UNSET",
                    1: "OK",
                    2: "ERROR",
                }
                status = status_map.get(span.status.code, "UNSET")

                spans.append({
                    "trace_id": span.trace_id.hex(),
                    "span_id": span.span_id.hex(),
                    "parent_span_id": span.parent_span_id.hex() if span.parent_span_id else None,
                    "name": span.name,
                    "service_name": service_name,
                    "start_time_ms": start_ms,
                    "end_time_ms": end_ms,
                    "duration_ms": duration_ms,
                    "status": status,
                    "attributes": _extract_attributes(span.attributes),
                })

    return spans


def parse_metrics_request(body: bytes) -> list[dict]:
    """
    Parse OTLP MetricsData protobuf into list of metric point dicts.

    Handles Gauge and Histogram types. For histograms, includes approx percentiles.

    Returns:
        List of dicts with keys:
        - name: metric name
        - value: numeric value (or None for histogram)
        - timestamp_ms: milliseconds since epoch
        - attributes: dict
        - percentiles (for histograms): dict with p50, p95, p99
    """
    metrics_data = metrics_pb2.MetricsData()
    metrics_data.ParseFromString(body)

    points = []
    current_time_ms = int(time.time() * 1000)

    for resource_metric in metrics_data.resource_metrics:
        for scope_metric in resource_metric.scope_metrics:
            for metric in scope_metric.metrics:
                # Handle Gauge
                if metric.HasField("gauge"):
                    for dp in metric.gauge.data_points:
                        timestamp_ms = _nanoseconds_to_milliseconds(dp.time_unix_nano)
                        if timestamp_ms == 0:
                            timestamp_ms = current_time_ms

                        value = None
                        if dp.HasField("as_int"):
                            value = dp.as_int
                        elif dp.HasField("as_double"):
                            value = dp.as_double

                        points.append({
                            "name": metric.name,
                            "value": value,
                            "timestamp_ms": timestamp_ms,
                            "attributes": _extract_attributes(dp.attributes),
                        })

                # Handle Sum (Counter)
                elif metric.HasField("sum"):
                    for dp in metric.sum.data_points:
                        timestamp_ms = _nanoseconds_to_milliseconds(dp.time_unix_nano)
                        if timestamp_ms == 0:
                            timestamp_ms = current_time_ms

                        value = None
                        if dp.HasField("as_int"):
                            value = dp.as_int
                        elif dp.HasField("as_double"):
                            value = dp.as_double

                        points.append({
                            "name": metric.name,
                            "value": value,
                            "timestamp_ms": timestamp_ms,
                            "attributes": _extract_attributes(dp.attributes),
                        })

                # Handle Histogram
                elif metric.HasField("histogram"):
                    for dp in metric.histogram.data_points:
                        timestamp_ms = _nanoseconds_to_milliseconds(dp.time_unix_nano)
                        if timestamp_ms == 0:
                            timestamp_ms = current_time_ms

                        # Extract approximate percentiles from histogram buckets
                        percentiles = _compute_histogram_percentiles(
                            dp.explicit_bounds, dp.bucket_counts
                        )

                        points.append({
                            "name": metric.name,
                            "value": dp.sum if dp.HasField("sum") else None,
                            "timestamp_ms": timestamp_ms,
                            "attributes": _extract_attributes(dp.attributes),
                            "percentiles": percentiles,
                            "count": dp.count,
                        })

    return points


def _compute_histogram_percentiles(
    bounds: list[float], counts: list[int]
) -> dict[str, float]:
    """
    Compute approximate P50, P95, P99 from histogram explicit bounds and bucket counts.

    This is a simplified percentile estimation that assumes uniform distribution
    within each bucket.
    """
    percentiles = {}
    total = sum(counts)

    if total == 0:
        return {"p50": 0.0, "p95": 0.0, "p99": 0.0}

    # Calculate cumulative counts
    cumulative = []
    cum = 0
    for count in counts:
        cum += count
        cumulative.append(cum)

    def find_percentile(p: float) -> float:
        target = total * p / 100.0
        for i, cum_count in enumerate(cumulative):
            if cum_count >= target:
                if i == 0:
                    return bounds[0] if bounds else 0.0
                # Linear interpolation within bucket
                lower_bound = bounds[i - 1] if i > 0 else 0.0
                upper_bound = bounds[i] if i < len(bounds) else bounds[-1]
                prev_cum = cumulative[i - 1] if i > 0 else 0
                bucket_range = upper_bound - lower_bound
                pos_in_bucket = (target - prev_cum) / (cum_count - prev_cum) if (cum_count - prev_cum) > 0 else 0
                return lower_bound + pos_in_bucket * bucket_range
        return bounds[-1] if bounds else 0.0

    percentiles["p50"] = find_percentile(50)
    percentiles["p95"] = find_percentile(95)
    percentiles["p99"] = find_percentile(99)

    return percentiles


def parse_logs_request(body: bytes) -> list[dict]:
    """
    Parse OTLP LogsData protobuf into list of log record dicts.

    Returns:
        List of dicts with keys:
        - timestamp_ms: milliseconds since epoch
        - severity: "TRACE", "DEBUG", "INFO", "WARN", "ERROR", "FATAL"
        - body: log message
        - trace_id: hex string (if present)
        - span_id: hex string (if present)
        - attributes: dict
    """
    logs_data = logs_pb2.LogsData()
    logs_data.ParseFromString(body)

    records = []
    for resource_log in logs_data.resource_logs:
        for scope_log in resource_log.scope_logs:
            for log_record in scope_log.log_records:
                timestamp_ms = _nanoseconds_to_milliseconds(log_record.time_unix_nano)

                # Map severity code to string
                severity_map = {
                    0: "TRACE",
                    1: "TRACE",
                    2: "DEBUG",
                    3: "DEBUG",
                    4: "INFO",
                    5: "INFO",
                    6: "WARN",
                    7: "WARN",
                    8: "ERROR",
                    9: "ERROR",
                    10: "FATAL",
                    11: "FATAL",
                }
                severity = severity_map.get(log_record.severity_number, "INFO")

                records.append({
                    "timestamp_ms": timestamp_ms,
                    "severity": severity,
                    "body": log_record.body.string_value if log_record.HasField("body") else "",
                    "trace_id": log_record.trace_id.hex() if log_record.trace_id else None,
                    "span_id": log_record.span_id.hex() if log_record.span_id else None,
                    "attributes": _extract_attributes(log_record.attributes),
                })

    return records
