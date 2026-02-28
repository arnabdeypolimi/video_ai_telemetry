from __future__ import annotations

import asyncio
import logging
from typing import Any

from video_ai_telemetry.conventions.attributes import TransportAttributes

logger = logging.getLogger("video_ai_telemetry.transport")


class WebRTCMetricsAdapter:
    def __init__(self, peer_connection: Any, poll_interval_s: float = 2.0, meter: Any = None):
        self._pc = peer_connection
        self._interval_s = poll_interval_s
        self._meter = meter
        self._task: asyncio.Task | None = None
        self._histograms = {}

    def start(self):
        if self._meter:
            self._histograms = {
                "rtt": self._meter.create_histogram("rt_video.transport.rtt", unit="ms"),
                "jitter": self._meter.create_histogram("rt_video.transport.jitter", unit="ms"),
                "packet_loss": self._meter.create_histogram(
                    "rt_video.transport.packet_loss", unit="%"
                ),
                "frame_rate": self._meter.create_histogram(
                    "rt_video.transport.frame_rate", unit="fps"
                ),
                "bitrate": self._meter.create_histogram("rt_video.transport.bitrate", unit="kbps"),
            }
        self._task = asyncio.ensure_future(self._poll_loop())

    async def stop(self):
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _poll_loop(self):
        while True:
            try:
                await self._poll_stats()
            except Exception as exc:
                logger.debug("WebRTC stats poll failed: %s", exc)
            await asyncio.sleep(self._interval_s)

    async def _poll_stats(self):
        try:
            stats = await self._pc.getStats()
        except Exception:
            return

        for report in stats.values():
            attrs = {TransportAttributes.PROTOCOL: "webrtc"}

            if report.type == "outbound-rtp":
                stream = "video" if report.kind == "video" else "audio"
                attrs[TransportAttributes.STREAM] = stream
                if hasattr(report, "framesPerSecond") and report.framesPerSecond:
                    self._record("frame_rate", float(report.framesPerSecond), attrs)

            elif report.type == "remote-inbound-rtp":
                if hasattr(report, "roundTripTime") and report.roundTripTime:
                    self._record("rtt", report.roundTripTime * 1000, attrs)
                if hasattr(report, "jitter") and report.jitter:
                    self._record("jitter", report.jitter * 1000, attrs)
                if hasattr(report, "packetsLost") and hasattr(report, "packetsReceived"):
                    total = report.packetsLost + report.packetsReceived
                    if total > 0:
                        loss_pct = (report.packetsLost / total) * 100
                        self._record("packet_loss", loss_pct, attrs)

    def _record(self, metric_key: str, value: float, attrs: dict):
        histogram = self._histograms.get(metric_key)
        if histogram:
            histogram.record(value, attrs)
