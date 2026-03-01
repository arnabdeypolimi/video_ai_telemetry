"""modaltrace: OpenTelemetry observability for real-time AI avatar and video pipelines.

Everything a user needs is importable from `modaltrace` directly:

    import modaltrace

    sdk = modaltrace.init(service_name="artalk-avatar")

    @modaltrace.pipeline_stage("flame_inference")
    async def run_model(...): ...

    async with modaltrace.stage("render") as s:
        s.record("vertex_count", 12345)

    modaltrace.info("Pipeline started", target_fps=30)
"""

from __future__ import annotations

from typing import Any

from modaltrace._version import __version__
from modaltrace.logging.api import (
    debug,
    error,
    exception,
    info,
    notice,
    warning,
)
from modaltrace.logging.api import (
    trace_log as trace,
)
from modaltrace.tracing.pipeline import async_stage, pipeline_stage, stage

__all__ = [
    "__version__",
    "init",
    "pipeline_stage",
    "stage",
    "async_stage",
    "trace",
    "debug",
    "info",
    "notice",
    "warning",
    "error",
    "exception",
]


class ModalTraceSDK:
    """SDK handle returned by init(). Context-manager compatible."""

    def __init__(
        self,
        config,
        tracer_provider,
        meter_provider,
        logger_provider,
        frame_aggregator,
        av_tracker,
        gpu_monitor=None,
        pending_processor=None,
    ):
        self._config = config
        self._tracer_provider = tracer_provider
        self._meter_provider = meter_provider
        self._logger_provider = logger_provider
        self.frame_aggregator = frame_aggregator
        self.av_tracker = av_tracker
        self._gpu_monitor = gpu_monitor
        self._pending_processor = pending_processor
        self._stopped = False

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.stop()

    def flush(self) -> None:
        """Force-flush all exporters."""
        self._tracer_provider.force_flush()
        self._meter_provider.force_flush()

    def stop(self) -> None:
        """Flush and shut down all components."""
        if self._stopped:
            return
        self._stopped = True

        self.frame_aggregator.stop()

        if self._pending_processor is not None:
            self._pending_processor.stop()

        if self._gpu_monitor is not None:
            self._gpu_monitor.stop()

        from modaltrace.instrumentation.eventloop import uninstall_eventloop_monitor
        from modaltrace.instrumentation.pytorch import uninstrument_pytorch
        from modaltrace.tracing.propagation import unpatch_all

        uninstrument_pytorch()
        unpatch_all()
        uninstall_eventloop_monitor()

        self._tracer_provider.shutdown()
        self._meter_provider.shutdown()
        self._logger_provider.shutdown()


def init(**kwargs: Any) -> ModalTraceSDK:
    """Initialize modaltrace. One-liner to get full observability.

    All kwargs are passed to ModalTraceConfig (Pydantic Settings), which also
    reads from MODALTRACE_* environment variables and .env files.

    Returns an ModalTraceSDK handle with .frame_aggregator, .av_tracker,
    .flush(), and .stop() methods. Also works as a context manager.
    """
    from modaltrace import _registry
    from modaltrace.config import ModalTraceConfig
    from modaltrace.exporters.setup import (
        create_resource,
        setup_logger_provider,
        setup_meter_provider,
        setup_tracer_provider,
    )
    from modaltrace.instrumentation.eventloop import install_eventloop_monitor
    from modaltrace.instrumentation.gpu import GPUMonitor
    from modaltrace.instrumentation.pytorch import instrument_pytorch
    from modaltrace.logging.api import _init_logging
    from modaltrace.logging.scrubber import ScrubbingSpanProcessor
    from modaltrace.metrics.aggregator import FrameMetricsAggregator
    from modaltrace.metrics.av_sync import AVSyncTracker
    from modaltrace.metrics.instruments import MetricInstruments
    from modaltrace.tracing.pending import PendingSpanProcessor
    from modaltrace.tracing.propagation import patch_all
    from modaltrace.tracing.sampler import AdaptiveSampler

    config = ModalTraceConfig(**kwargs)
    _registry._config = config

    resource = create_resource(config)
    tracer_provider = setup_tracer_provider(config, resource)
    meter_provider = setup_meter_provider(config, resource)
    logger_provider = setup_logger_provider(config, resource)

    tracer = tracer_provider.get_tracer("modaltrace", __version__)
    meter = meter_provider.get_meter("modaltrace", __version__)
    _registry._tracer = tracer
    _registry._meter = meter

    instruments = MetricInstruments(meter)

    if config.scrubbing_enabled:
        scrubber = ScrubbingSpanProcessor(
            extra_patterns=config.scrubbing_patterns,
            callback=config.scrubbing_callback,
        )
        tracer_provider.add_span_processor(scrubber)

    from modaltrace.exporters.setup import _create_span_exporter

    pending_exporter = _create_span_exporter(config)
    pending_processor = PendingSpanProcessor(
        exporter=pending_exporter,
        flush_interval_ms=config.pending_span_flush_interval_ms,
    )
    tracer_provider.add_span_processor(pending_processor)
    pending_processor.start()

    aggregator = FrameMetricsAggregator(
        instruments=instruments,
        buffer_size=config.ring_buffer_size,
        flush_interval_ms=config.metrics_flush_interval_ms,
    )
    aggregator.start()

    av_tracker = AVSyncTracker(
        instruments=instruments,
        drift_warning_ms=config.av_drift_warning_ms,
        chunk_ttl_s=config.av_chunk_ttl_s,
        jitter_window=config.av_jitter_window,
        warning_callback=warning,
    )

    sampler = AdaptiveSampler(
        window_s=config.span_window_s,
        anomaly_threshold_ms=config.anomaly_threshold_ms,
    )
    _registry._sampler = sampler

    gpu_monitor = None
    if config.gpu_monitoring:
        gpu_monitor = GPUMonitor(
            poll_interval_s=config.gpu_poll_interval_s,
            device_indices=config.gpu_device_indices,
        )
        if gpu_monitor.start():
            gpu_monitor.register_gauges(meter)
        else:
            gpu_monitor = None

    if config.pytorch_instrumentation:
        instrument_pytorch(
            tracer=tracer,
            sample_rate=config.pytorch_sample_rate,
            anomaly_threshold_ms=config.anomaly_threshold_ms,
            track_memory=config.pytorch_track_memory,
            track_shapes=config.pytorch_track_shapes,
            aggregator=aggregator,
        )

    if config.threadpool_propagation:
        patch_all()

    if config.eventloop_monitoring:
        install_eventloop_monitor(
            threshold_ms=config.eventloop_lag_threshold_ms,
            warning_callback=warning,
        )

    _init_logging(
        logger_provider=logger_provider,
        log_level=config.log_level,
        log_console=config.log_console,
    )

    sdk = ModalTraceSDK(
        config=config,
        tracer_provider=tracer_provider,
        meter_provider=meter_provider,
        logger_provider=logger_provider,
        frame_aggregator=aggregator,
        av_tracker=av_tracker,
        gpu_monitor=gpu_monitor,
        pending_processor=pending_processor,
    )
    _registry._sdk = sdk

    return sdk
