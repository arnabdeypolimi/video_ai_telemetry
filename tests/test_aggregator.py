"""Tests for FrameMetricsAggregator and ring buffer."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from modaltrace.metrics.aggregator import FrameMetricsAggregator, _RingBuffer


class TestRingBuffer:
    def test_write_and_drain(self):
        buf = _RingBuffer(capacity=4)
        buf.write(1.0)
        buf.write(2.0)
        buf.write(3.0)
        assert buf.drain() == [1.0, 2.0, 3.0]

    def test_drain_empty(self):
        buf = _RingBuffer(capacity=4)
        assert buf.drain() == []

    def test_wrap_around(self):
        buf = _RingBuffer(capacity=4)
        for i in range(6):
            buf.write(float(i))
        # Should contain last 4 values: 2.0, 3.0, 4.0, 5.0
        result = buf.drain()
        assert result == [2.0, 3.0, 4.0, 5.0]

    def test_drain_resets(self):
        buf = _RingBuffer(capacity=4)
        buf.write(1.0)
        buf.drain()
        assert buf.drain() == []

    def test_exact_capacity(self):
        buf = _RingBuffer(capacity=4)
        for i in range(4):
            buf.write(float(i))
        assert buf.drain() == [0.0, 1.0, 2.0, 3.0]


class TestFrameMetricsAggregator:
    @pytest.fixture
    def mock_instruments(self):
        instruments = MagicMock()
        instruments.forward_pass_duration = MagicMock()
        instruments.render_frame_duration = MagicMock()
        instruments.encode_frame_duration = MagicMock()
        instruments.audio_chunk_duration = MagicMock()
        return instruments

    def test_record_and_flush(self, mock_instruments):
        agg = FrameMetricsAggregator(
            instruments=mock_instruments, buffer_size=16, flush_interval_ms=10_000
        )
        agg.record(forward_pass_ms=11.2, render_ms=3.1)
        agg.record(forward_pass_ms=12.0)

        # Manual flush
        agg._flush()

        assert mock_instruments.forward_pass_duration.record.call_count == 2
        assert mock_instruments.render_frame_duration.record.call_count == 1

    def test_unknown_keys_ignored(self, mock_instruments):
        agg = FrameMetricsAggregator(
            instruments=mock_instruments, buffer_size=16, flush_interval_ms=10_000
        )
        agg.record(forward_pass_ms=1.0, unknown_metric=99.0)
        agg._flush()

        assert mock_instruments.forward_pass_duration.record.call_count == 1

    def test_start_stop(self, mock_instruments):
        agg = FrameMetricsAggregator(
            instruments=mock_instruments, buffer_size=16, flush_interval_ms=50
        )
        agg.start()
        agg.record(forward_pass_ms=10.0)
        agg.stop()

        assert mock_instruments.forward_pass_duration.record.call_count >= 1

    def test_ring_buffer_overflow(self, mock_instruments):
        agg = FrameMetricsAggregator(
            instruments=mock_instruments, buffer_size=4, flush_interval_ms=10_000
        )
        for i in range(8):
            agg.record(forward_pass_ms=float(i))
        agg._flush()

        # Only last 4 samples should be flushed
        assert mock_instruments.forward_pass_duration.record.call_count == 4
        calls = [c.args[0] for c in mock_instruments.forward_pass_duration.record.call_args_list]
        assert calls == [4.0, 5.0, 6.0, 7.0]
