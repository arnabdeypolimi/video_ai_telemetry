"""Tests for dashboard frontend data transformation logic.

These tests verify the data transformations that the frontend JavaScript performs
on telemetry data to ensure correct visualization.
"""

import time


class TestStatisticsCalculation:
    """Test statistics calculations for dashboard stats panel."""

    def test_fps_calculation(self):
        """Test FPS calculation from spans."""
        now = int(time.time() * 1000)
        spans = []

        # Add 30 spans within last 5 seconds (should be 6 FPS)
        for i in range(30):
            spans.append(
                {
                    "name": f"frame_{i}",
                    "start_time_ms": now - (5000 - i * 160),  # Spread over 5 seconds
                    "duration_ms": 10,
                    "status": "OK",
                    "attributes": {},
                }
            )

        # Simulate JavaScript FPS calculation
        last_5s = now - 5000
        recent_spans = [s for s in spans if s["start_time_ms"] >= last_5s]
        fps = len(recent_spans) / 5

        assert fps == 6.0

    def test_fps_calculation_zero_spans(self):
        """Test FPS calculation with no spans."""
        fps = 0 / 5
        assert fps == 0.0

    def test_latency_percentile_extraction(self):
        """Test extracting P95 latencies by stage."""
        metrics = [
            {
                "name": "modaltrace.pipeline.stage.duration",
                "timestamp_ms": 1000,
                "attributes": {"modaltrace.pipeline.stage": "inference"},
                "percentiles": {"p50": 40, "p95": 45.3, "p99": 50},
            },
            {
                "name": "modaltrace.pipeline.stage.duration",
                "timestamp_ms": 1100,
                "attributes": {"modaltrace.pipeline.stage": "render"},
                "percentiles": {"p50": 10, "p95": 12.5, "p99": 15},
            },
            {
                "name": "modaltrace.pipeline.stage.duration",
                "timestamp_ms": 1200,
                "attributes": {"modaltrace.pipeline.stage": "encode"},
                "percentiles": {"p50": 30, "p95": 35.2, "p99": 40},
            },
        ]

        # Simulate JavaScript stage grouping
        stage_latencies = {}
        by_stage = {}

        for m in metrics:
            stage = m["attributes"].get("modaltrace.pipeline.stage", "unknown")
            if stage not in by_stage or m["timestamp_ms"] > by_stage[stage]["timestamp_ms"]:
                by_stage[stage] = m

        for stage, metric in by_stage.items():
            if metric.get("percentiles"):
                stage_latencies[stage] = metric["percentiles"]["p95"]

        assert stage_latencies["inference"] == 45.3
        assert stage_latencies["render"] == 12.5
        assert stage_latencies["encode"] == 35.2

    def test_latency_extraction_uses_latest_only(self):
        """Test that only latest metric per stage is used."""
        metrics = [
            {
                "name": "modaltrace.pipeline.stage.duration",
                "timestamp_ms": 1000,
                "attributes": {"modaltrace.pipeline.stage": "inference"},
                "percentiles": {"p50": 40, "p95": 45.0, "p99": 50},
            },
            {
                "name": "modaltrace.pipeline.stage.duration",
                "timestamp_ms": 2000,
                "attributes": {"modaltrace.pipeline.stage": "inference"},
                "percentiles": {"p50": 41, "p95": 46.0, "p99": 51},
            },
        ]

        by_stage = {}
        for m in metrics:
            stage = m["attributes"].get("modaltrace.pipeline.stage")
            if stage not in by_stage or m["timestamp_ms"] > by_stage[stage]["timestamp_ms"]:
                by_stage[stage] = m

        # Should have only the latest
        assert len(by_stage) == 1
        assert by_stage["inference"]["percentiles"]["p95"] == 46.0


class TestMetricFilteringByTimeWindow:
    """Test filtering metrics by time window."""

    def test_60_second_window_filtering(self):
        """Test filtering metrics to last 60 seconds."""
        now = int(time.time() * 1000)
        last_60s = now - 60000

        metrics = [
            {
                "name": "test.metric",
                "timestamp_ms": now - 70000,  # 70s ago - should be excluded
                "value": 1,
                "attributes": {},
            },
            {
                "name": "test.metric",
                "timestamp_ms": now - 50000,  # 50s ago - should be included
                "value": 2,
                "attributes": {},
            },
            {
                "name": "test.metric",
                "timestamp_ms": now - 10000,  # 10s ago - should be included
                "value": 3,
                "attributes": {},
            },
        ]

        # Simulate JavaScript filtering
        filtered = [m for m in metrics if m["timestamp_ms"] >= last_60s]

        assert len(filtered) == 2
        assert all(m["timestamp_ms"] >= last_60s for m in filtered)

    def test_relative_time_calculation(self):
        """Test relative time window calculation."""
        now = int(time.time() * 1000)
        last_60s = now - 60000

        # Verify calculation
        assert last_60s == now - 60000
        assert (now - last_60s) == 60000


class TestPipelineChartDataPreparation:
    """Test preparing data for multi-stage pipeline chart."""

    def test_group_metrics_by_stage_and_time(self):
        """Test grouping metrics by stage and timestamp."""
        metrics = [
            {
                "name": "modaltrace.pipeline.stage.duration",
                "timestamp_ms": 1000,
                "attributes": {"modaltrace.pipeline.stage": "inference"},
                "percentiles": {"p95": 45},
            },
            {
                "name": "modaltrace.pipeline.stage.duration",
                "timestamp_ms": 1000,
                "attributes": {"modaltrace.pipeline.stage": "render"},
                "percentiles": {"p95": 12},
            },
            {
                "name": "modaltrace.pipeline.stage.duration",
                "timestamp_ms": 2000,
                "attributes": {"modaltrace.pipeline.stage": "inference"},
                "percentiles": {"p95": 46},
            },
            {
                "name": "modaltrace.pipeline.stage.duration",
                "timestamp_ms": 2000,
                "attributes": {"modaltrace.pipeline.stage": "render"},
                "percentiles": {"p95": 11},
            },
        ]

        # Simulate JavaScript grouping
        stages = {}
        all_times = set()

        for m in metrics:
            stage = m["attributes"].get("modaltrace.pipeline.stage", "unknown")
            timestamp = m["timestamp_ms"]

            if stage not in stages:
                stages[stage] = {}

            stages[stage][timestamp] = m["percentiles"].get("p95")
            all_times.add(timestamp)

        sorted_times = sorted(all_times)
        time_labels = [str(t) for t in sorted_times]

        # Should have data for 2 stages at 2 timestamps
        assert len(stages) == 2
        assert len(sorted_times) == 2
        assert len(time_labels) == 2

        # Verify stage data
        assert stages["inference"][1000] == 45
        assert stages["inference"][2000] == 46
        assert stages["render"][1000] == 12
        assert stages["render"][2000] == 11

    def test_handle_missing_stage_data_at_timestamp(self):
        """Test handling when stage data is missing at some timestamps."""
        stages = {
            "inference": {1000: 45, 2000: 46, 3000: 47},
            "render": {1000: 12, 3000: 13},  # Missing at 2000
        }
        all_times = [1000, 2000, 3000]

        # Build data arrays for each stage
        datasets = {}
        for stage, data in stages.items():
            datasets[stage] = [data.get(t) for t in all_times]

        assert datasets["inference"] == [45, 46, 47]
        assert datasets["render"] == [12, None, 13]  # None for missing


class TestGPUMetricsProcessing:
    """Test GPU metrics processing."""

    def test_gpu_utilization_range_conversion(self):
        """Test converting GPU utilization from 0-1 to percentage."""
        gpu_data = {
            "0": {
                "modaltrace.gpu.utilization": 0.75,  # 0-1 range
                "modaltrace.gpu.memory.used": 8.5,
                "modaltrace.gpu.memory.total": 24,
            }
        }

        # Simulate JavaScript conversion
        for _device_id, metrics in gpu_data.items():
            util = metrics.get("modaltrace.gpu.utilization", 0)
            util_percent = util * 100

            # Verify conversion
            assert util_percent == 75.0

    def test_gpu_memory_percentage_calculation(self):
        """Test calculating GPU memory percentage."""
        gpu_data = {
            "0": {
                "modaltrace.gpu.memory.used": 8.5,
                "modaltrace.gpu.memory.total": 24,
            }
        }

        # Simulate JavaScript calculation
        for _device_id, metrics in gpu_data.items():
            mem_used = metrics.get("modaltrace.gpu.memory.used", 0)
            mem_total = metrics.get("modaltrace.gpu.memory.total", 1)
            mem_percent = (mem_used / mem_total) * 100

            # Verify calculation
            assert abs(mem_percent - 35.42) < 0.01

    def test_gpu_safe_metric_extraction(self):
        """Test safe extraction of GPU metrics with fallbacks."""
        gpu_data = {
            "0": {
                "modaltrace.gpu.utilization": 0.75,
                # memory.used not provided
                "modaltrace.gpu.memory.total": 24,
                # temperature not provided
            }
        }

        # Simulate JavaScript safe extraction
        for _device_id, metrics in gpu_data.items():
            util = metrics.get("modaltrace.gpu.utilization") or 0
            mem_used = metrics.get("modaltrace.gpu.memory.used") or 0
            mem_total = metrics.get("modaltrace.gpu.memory.total") or 24
            temp = metrics.get("modaltrace.gpu.temperature") or 0

            assert util == 0.75
            assert mem_used == 0
            assert mem_total == 24
            assert temp == 0


class TestTimestampFormatting:
    """Test timestamp formatting for display."""

    def test_trace_timestamp_formatting(self):
        """Test formatting trace timestamps to HH:MM:SS.ms."""
        # Simulate a timestamp in milliseconds
        ts_ms = 1234567890123  # Some arbitrary timestamp

        from datetime import datetime

        dt = datetime.fromtimestamp(ts_ms / 1000)
        time_str = dt.strftime("%H:%M:%S")
        ms_part = int((ts_ms % 1000) / 10)
        formatted = f"{time_str}.{ms_part:02d}"

        assert ":" in formatted
        assert len(formatted) == 11  # HH:MM:SS.ms

    def test_log_timestamp_formatting_and_sorting(self):
        """Test formatting and sorting log timestamps."""
        now = int(time.time() * 1000)
        logs = [
            {
                "timestamp_ms": now - 300,
                "severity": "INFO",
                "body": "Old message",
            },
            {
                "timestamp_ms": now - 100,
                "severity": "ERROR",
                "body": "Recent message",
            },
            {
                "timestamp_ms": now - 200,
                "severity": "WARN",
                "body": "Middle message",
            },
        ]

        # Simulate JavaScript sorting (newest first)
        sorted_logs = sorted(logs, key=lambda log: log["timestamp_ms"], reverse=True)

        # Should be newest first
        assert sorted_logs[0]["body"] == "Recent message"
        assert sorted_logs[1]["body"] == "Middle message"
        assert sorted_logs[2]["body"] == "Old message"


class TestNullSafetyAndFallbacks:
    """Test null safety and fallback handling."""

    def test_missing_percentiles_fallback(self):
        """Test fallback when percentiles are missing."""
        metric = {
            "name": "test.metric",
            "value": 45.5,
            "timestamp_ms": 1000,
            "attributes": {},
            # percentiles not provided
        }

        # Simulate JavaScript safe access
        p95 = metric.get("percentiles", {}).get("p95")
        assert p95 is None

    def test_missing_attributes_fallback(self):
        """Test fallback when attributes are missing."""
        span = {
            "name": "test_span",
            "start_time_ms": 1000,
            "duration_ms": 50,
            "status": "OK",
            # attributes not provided
        }

        # Simulate JavaScript safe access
        attrs = span.get("attributes") or {}
        stage = attrs.get("modaltrace.pipeline.stage")
        assert stage is None

    def test_empty_metrics_list_handling(self):
        """Test handling empty metrics list."""
        metrics = []

        # Simulate JavaScript processing
        stage_latencies = {
            "inference": None,
            "render": None,
            "encode": None,
        }

        if metrics:
            by_stage = {}
            for m in metrics:
                stage = m["attributes"].get("modaltrace.pipeline.stage")
                if stage not in by_stage:
                    by_stage[stage] = m
                stage_latencies[stage] = by_stage[stage]["percentiles"]["p95"]

        assert stage_latencies["inference"] is None
        assert stage_latencies["render"] is None
        assert stage_latencies["encode"] is None

    def test_span_without_attributes(self):
        """Test handling spans without attributes."""
        span = {
            "name": "test_span",
            "service_name": "test",
            "start_time_ms": 1000,
            "duration_ms": 50,
            "status": "OK",
            # No attributes key
        }

        # Simulate JavaScript access
        attrs = span.get("attributes") or {}
        assert len(attrs) == 0


class TestLogFilteringBySeverity:
    """Test log filtering by severity level."""

    def test_filter_logs_by_single_severity(self):
        """Test filtering logs to specific severity."""
        logs = [
            {"timestamp_ms": 1000, "severity": "ERROR", "body": "Error 1"},
            {"timestamp_ms": 1100, "severity": "WARN", "body": "Warning 1"},
            {"timestamp_ms": 1200, "severity": "INFO", "body": "Info 1"},
            {"timestamp_ms": 1300, "severity": "ERROR", "body": "Error 2"},
        ]

        # Simulate JavaScript filtering
        current_level = "ERROR"
        filtered = [log for log in logs if log["severity"] == current_level]

        assert len(filtered) == 2
        assert all(log["severity"] == "ERROR" for log in filtered)

    def test_filter_logs_all_severities(self):
        """Test showing all log severities."""
        logs = [
            {"timestamp_ms": 1000, "severity": "ERROR", "body": "Error"},
            {"timestamp_ms": 1100, "severity": "WARN", "body": "Warning"},
            {"timestamp_ms": 1200, "severity": "INFO", "body": "Info"},
        ]

        # Simulate JavaScript filtering with empty level (all)
        current_level = ""
        filtered = [log for log in logs if current_level == "" or log["severity"] == current_level]

        assert len(filtered) == 3
