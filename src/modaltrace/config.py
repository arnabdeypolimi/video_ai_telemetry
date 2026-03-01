"""Pydantic Settings model — single source of truth for all configuration.

Users can configure via Python kwargs, environment variables (MODALTRACE_*), or .env files.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Literal

from pydantic import AnyHttpUrl, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ModalTraceConfig(BaseSettings):
    """Configuration for modaltrace SDK."""

    # ── Identity ──────────────────────────────────────────────────────────
    service_name: str = "modaltrace-pipeline"
    service_version: str = "0.0.0"
    deployment_environment: str = "development"

    # ── OTLP Export ───────────────────────────────────────────────────────
    otlp_endpoint: AnyHttpUrl = "http://localhost:4318"  # type: ignore[assignment]
    otlp_protocol: Literal["http", "grpc"] = "http"
    otlp_headers: dict[str, str] = Field(default_factory=dict)
    otlp_timeout_ms: int = 10_000

    # ── Feature Flags ─────────────────────────────────────────────────────
    pytorch_instrumentation: bool = True
    gpu_monitoring: bool = True
    webrtc_monitoring: bool = False
    eventloop_monitoring: bool = True
    threadpool_propagation: bool = True

    # ── Frame Metrics Aggregator ──────────────────────────────────────────
    metrics_flush_interval_ms: int = 1_000
    ring_buffer_size: int = 512

    # ── Adaptive Sampler ──────────────────────────────────────────────────
    span_window_s: float = 1.0
    anomaly_threshold_ms: float = 50.0
    pytorch_sample_rate: float = 0.01

    # ── Pending Spans ─────────────────────────────────────────────────────
    pending_span_flush_interval_ms: int = 5_000

    # ── A/V Sync ──────────────────────────────────────────────────────────
    av_drift_warning_ms: float = 40.0
    av_chunk_ttl_s: float = 5.0
    av_jitter_window: int = 30

    # ── GPU Monitor ───────────────────────────────────────────────────────
    gpu_poll_interval_s: float = 1.0
    gpu_device_indices: list[int] | None = None

    # ── PyTorch Instrumentation ───────────────────────────────────────────
    pytorch_track_memory: bool = True
    pytorch_track_shapes: bool = False

    # ── PII Scrubbing ─────────────────────────────────────────────────────
    scrubbing_enabled: bool = True
    scrubbing_patterns: list[str] = Field(default_factory=list)
    scrubbing_callback: Callable | None = None

    # ── Structured Logging ────────────────────────────────────────────────
    log_level: str = "info"
    log_console: bool = True

    # ── Event Loop Monitor ────────────────────────────────────────────────
    eventloop_lag_threshold_ms: float = 100.0

    model_config = SettingsConfigDict(
        env_prefix="MODALTRACE_",
        env_file=".env",
        env_file_encoding="utf-8",
        arbitrary_types_allowed=True,
    )

    @field_validator("ring_buffer_size")
    @classmethod
    def must_be_power_of_two(cls, v: int) -> int:
        if v & (v - 1) != 0:
            raise ValueError(f"ring_buffer_size must be a power of 2, got {v}")
        return v

    @field_validator("pytorch_sample_rate")
    @classmethod
    def must_be_fraction(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError(f"pytorch_sample_rate must be between 0 and 1, got {v}")
        return v
