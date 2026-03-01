"""Tests for WebRTCMetricsAdapter — uses mocked aiortc peer connection."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from modaltrace.instrumentation.transport import WebRTCMetricsAdapter

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_report(**kwargs):
    """Create a simple namespace-like object mimicking an aiortc RTCStats report."""
    report = MagicMock()
    for key, val in kwargs.items():
        setattr(report, key, val)
    return report


def _make_pc(stats: dict | None = None, raise_on_get_stats: bool = False):
    """Return a mock RTCPeerConnection."""
    pc = MagicMock()
    if raise_on_get_stats:
        pc.getStats = AsyncMock(side_effect=RuntimeError("connection closed"))
    else:
        pc.getStats = AsyncMock(return_value=stats or {})
    return pc


def _make_meter():
    """Return a mock OTel Meter."""
    meter = MagicMock()
    meter.create_histogram = MagicMock(side_effect=lambda *a, **kw: MagicMock())
    return meter


# ---------------------------------------------------------------------------
# 1. Start / stop lifecycle
# ---------------------------------------------------------------------------


class TestLifecycle:
    @pytest.mark.asyncio
    async def test_start_creates_task(self):
        pc = _make_pc()
        adapter = WebRTCMetricsAdapter(pc, poll_interval_s=100.0)
        adapter.start()
        assert adapter._task is not None
        assert not adapter._task.done()
        await adapter.stop()

    @pytest.mark.asyncio
    async def test_stop_cancels_task(self):
        pc = _make_pc()
        adapter = WebRTCMetricsAdapter(pc, poll_interval_s=100.0)
        adapter.start()
        task = adapter._task
        await adapter.stop()
        assert task.cancelled() or task.done()

    @pytest.mark.asyncio
    async def test_stop_before_start_is_safe(self):
        pc = _make_pc()
        adapter = WebRTCMetricsAdapter(pc, poll_interval_s=100.0)
        # Should not raise even though start() was never called
        await adapter.stop()

    @pytest.mark.asyncio
    async def test_start_with_meter_creates_histograms(self):
        pc = _make_pc()
        meter = _make_meter()
        adapter = WebRTCMetricsAdapter(pc, poll_interval_s=100.0, meter=meter)
        adapter.start()
        assert meter.create_histogram.call_count == 5
        histogram_names = {call.args[0] for call in meter.create_histogram.call_args_list}
        assert "modaltrace.transport.rtt" in histogram_names
        assert "modaltrace.transport.jitter" in histogram_names
        assert "modaltrace.transport.packet_loss" in histogram_names
        assert "modaltrace.transport.frame_rate" in histogram_names
        assert "modaltrace.transport.bitrate" in histogram_names
        await adapter.stop()

    @pytest.mark.asyncio
    async def test_start_without_meter_skips_histograms(self):
        pc = _make_pc()
        adapter = WebRTCMetricsAdapter(pc, poll_interval_s=100.0, meter=None)
        adapter.start()
        assert adapter._histograms == {}
        await adapter.stop()


# ---------------------------------------------------------------------------
# 2. Stats parsing from mock reports
# ---------------------------------------------------------------------------


class TestStatsParsing:
    @pytest.mark.asyncio
    async def test_outbound_rtp_video_frame_rate(self):
        report = _make_report(type="outbound-rtp", kind="video", framesPerSecond=30.0)
        pc = _make_pc(stats={"r1": report})
        meter = _make_meter()
        adapter = WebRTCMetricsAdapter(pc, poll_interval_s=100.0, meter=meter)
        adapter.start()

        await adapter._poll_stats()

        frame_rate_hist = adapter._histograms["frame_rate"]
        frame_rate_hist.record.assert_called_once()
        call_args = frame_rate_hist.record.call_args
        assert call_args.args[0] == 30.0
        assert call_args.args[1]["modaltrace.transport.protocol"] == "webrtc"
        assert call_args.args[1]["modaltrace.transport.stream"] == "video"

        await adapter.stop()

    @pytest.mark.asyncio
    async def test_outbound_rtp_audio_stream_label(self):
        report = _make_report(type="outbound-rtp", kind="audio", framesPerSecond=None)
        pc = _make_pc(stats={"r1": report})
        meter = _make_meter()
        adapter = WebRTCMetricsAdapter(pc, poll_interval_s=100.0, meter=meter)
        adapter.start()

        await adapter._poll_stats()

        # framesPerSecond is None/falsy so frame_rate histogram should NOT be called
        frame_rate_hist = adapter._histograms["frame_rate"]
        frame_rate_hist.record.assert_not_called()

        await adapter.stop()

    @pytest.mark.asyncio
    async def test_remote_inbound_rtp_rtt(self):
        report = _make_report(
            type="remote-inbound-rtp",
            roundTripTime=0.050,  # 50 ms in seconds
            jitter=None,
        )
        del report.packetsLost  # ensure hasattr returns False
        del report.packetsReceived
        pc = _make_pc(stats={"r1": report})
        meter = _make_meter()
        adapter = WebRTCMetricsAdapter(pc, poll_interval_s=100.0, meter=meter)
        adapter.start()

        await adapter._poll_stats()

        rtt_hist = adapter._histograms["rtt"]
        rtt_hist.record.assert_called_once()
        recorded_value = rtt_hist.record.call_args.args[0]
        assert abs(recorded_value - 50.0) < 0.001  # 0.050 s * 1000 = 50 ms

        await adapter.stop()

    @pytest.mark.asyncio
    async def test_remote_inbound_rtp_jitter(self):
        report = _make_report(
            type="remote-inbound-rtp",
            roundTripTime=None,
            jitter=0.020,  # 20 ms in seconds
        )
        del report.packetsLost
        del report.packetsReceived
        pc = _make_pc(stats={"r1": report})
        meter = _make_meter()
        adapter = WebRTCMetricsAdapter(pc, poll_interval_s=100.0, meter=meter)
        adapter.start()

        await adapter._poll_stats()

        jitter_hist = adapter._histograms["jitter"]
        jitter_hist.record.assert_called_once()
        recorded_value = jitter_hist.record.call_args.args[0]
        assert abs(recorded_value - 20.0) < 0.001

        await adapter.stop()

    @pytest.mark.asyncio
    async def test_remote_inbound_rtp_packet_loss(self):
        report = _make_report(
            type="remote-inbound-rtp",
            roundTripTime=None,
            jitter=None,
            packetsLost=10,
            packetsReceived=90,
        )
        pc = _make_pc(stats={"r1": report})
        meter = _make_meter()
        adapter = WebRTCMetricsAdapter(pc, poll_interval_s=100.0, meter=meter)
        adapter.start()

        await adapter._poll_stats()

        loss_hist = adapter._histograms["packet_loss"]
        loss_hist.record.assert_called_once()
        recorded_value = loss_hist.record.call_args.args[0]
        # 10 / (10 + 90) * 100 = 10%
        assert abs(recorded_value - 10.0) < 0.001

        await adapter.stop()

    @pytest.mark.asyncio
    async def test_zero_total_packets_skips_loss_recording(self):
        report = _make_report(
            type="remote-inbound-rtp",
            roundTripTime=None,
            jitter=None,
            packetsLost=0,
            packetsReceived=0,
        )
        pc = _make_pc(stats={"r1": report})
        meter = _make_meter()
        adapter = WebRTCMetricsAdapter(pc, poll_interval_s=100.0, meter=meter)
        adapter.start()

        await adapter._poll_stats()

        loss_hist = adapter._histograms["packet_loss"]
        loss_hist.record.assert_not_called()

        await adapter.stop()

    @pytest.mark.asyncio
    async def test_unknown_report_type_ignored(self):
        report = _make_report(type="candidate-pair", availableOutgoingBitrate=1234567)
        pc = _make_pc(stats={"r1": report})
        meter = _make_meter()
        adapter = WebRTCMetricsAdapter(pc, poll_interval_s=100.0, meter=meter)
        adapter.start()

        await adapter._poll_stats()

        # No histogram should have been recorded
        for hist in adapter._histograms.values():
            hist.record.assert_not_called()

        await adapter.stop()

    @pytest.mark.asyncio
    async def test_multiple_reports_processed(self):
        outbound = _make_report(type="outbound-rtp", kind="video", framesPerSecond=25.0)
        inbound = _make_report(
            type="remote-inbound-rtp",
            roundTripTime=0.100,
            jitter=0.005,
            packetsLost=5,
            packetsReceived=95,
        )
        pc = _make_pc(stats={"out": outbound, "in": inbound})
        meter = _make_meter()
        adapter = WebRTCMetricsAdapter(pc, poll_interval_s=100.0, meter=meter)
        adapter.start()

        await adapter._poll_stats()

        adapter._histograms["frame_rate"].record.assert_called_once()
        adapter._histograms["rtt"].record.assert_called_once()
        adapter._histograms["jitter"].record.assert_called_once()
        adapter._histograms["packet_loss"].record.assert_called_once()

        await adapter.stop()


# ---------------------------------------------------------------------------
# 3. Graceful degradation on getStats failure
# ---------------------------------------------------------------------------


class TestGracefulDegradation:
    @pytest.mark.asyncio
    async def test_get_stats_exception_does_not_raise(self):
        pc = _make_pc(raise_on_get_stats=True)
        meter = _make_meter()
        adapter = WebRTCMetricsAdapter(pc, poll_interval_s=100.0, meter=meter)
        adapter.start()

        # _poll_stats must swallow the exception silently
        await adapter._poll_stats()

        # No metrics should have been recorded
        for hist in adapter._histograms.values():
            hist.record.assert_not_called()

        await adapter.stop()

    @pytest.mark.asyncio
    async def test_poll_loop_continues_after_failure(self):
        """The poll loop must keep running even if individual polls fail."""
        call_count = 0

        async def flaky_get_stats():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise RuntimeError("transient error")
            return {}

        pc = MagicMock()
        pc.getStats = flaky_get_stats

        adapter = WebRTCMetricsAdapter(pc, poll_interval_s=0.01)
        adapter.start()

        # Give the loop a short window to run a few iterations
        await asyncio.sleep(0.08)
        await adapter.stop()

        assert call_count >= 3, "Poll loop did not recover after initial failures"

    @pytest.mark.asyncio
    async def test_no_meter_does_not_raise_on_record(self):
        """_record should be a no-op when no meter was provided."""
        report = _make_report(type="outbound-rtp", kind="video", framesPerSecond=24.0)
        pc = _make_pc(stats={"r1": report})
        adapter = WebRTCMetricsAdapter(pc, poll_interval_s=100.0, meter=None)
        adapter.start()

        # Should not raise even though _histograms is empty
        await adapter._poll_stats()

        await adapter.stop()

    @pytest.mark.asyncio
    async def test_stop_is_idempotent(self):
        """Calling stop() twice should not raise."""
        pc = _make_pc()
        adapter = WebRTCMetricsAdapter(pc, poll_interval_s=100.0)
        adapter.start()
        await adapter.stop()
        await adapter.stop()  # second call must be safe
