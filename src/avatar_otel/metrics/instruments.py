"""Pre-allocated OTel metric instruments.

All instruments are created once at init() time — never inside loops.
"""

from __future__ import annotations

from opentelemetry.metrics import Histogram, Counter, Meter


class MetricInstruments:
    """Holds all pre-allocated OTel metric instruments."""

    def __init__(self, meter: Meter) -> None:
        # ── Histograms ────────────────────────────────────────────────────
        self.forward_pass_duration: Histogram = meter.create_histogram(
            name="rt_video.inference.forward_pass.duration",
            description="Duration of model forward pass",
            unit="ms",
        )
        self.render_frame_duration: Histogram = meter.create_histogram(
            name="rt_video.render.frame.duration",
            description="Duration of frame rendering",
            unit="ms",
        )
        self.encode_frame_duration: Histogram = meter.create_histogram(
            name="rt_video.encode.frame.duration",
            description="Duration of frame encoding",
            unit="ms",
        )
        self.audio_chunk_duration: Histogram = meter.create_histogram(
            name="rt_video.audio.chunk.duration",
            description="Duration of audio chunk processing",
            unit="ms",
        )
        self.av_sync_drift: Histogram = meter.create_histogram(
            name="rt_video.av_sync.drift",
            description="Audio-video sync drift (positive = video lags audio)",
            unit="ms",
        )
        self.av_sync_jitter: Histogram = meter.create_histogram(
            name="rt_video.av_sync.jitter",
            description="Audio-video sync jitter (MAD of drift)",
            unit="ms",
        )
        self.pipeline_stage_duration: Histogram = meter.create_histogram(
            name="rt_video.pipeline.stage.duration",
            description="Duration of a pipeline stage",
            unit="ms",
        )

        # ── Counters ─────────────────────────────────────────────────────
        self.frames_processed: Counter = meter.create_counter(
            name="rt_video.frames.processed",
            description="Total frames processed",
            unit="frames",
        )
        self.frames_dropped: Counter = meter.create_counter(
            name="rt_video.frames.dropped",
            description="Total frames dropped",
            unit="frames",
        )
        self.av_sync_unmatched: Counter = meter.create_counter(
            name="rt_video.av_sync.unmatched_chunks",
            description="Audio chunks that expired without a matching frame",
            unit="chunks",
        )
