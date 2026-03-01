# modaltrace — Complete Library Plan

**Package:** `modaltrace` · **Import:** `import modaltrace` · **Python:** ≥3.10  
**License:** Apache-2.0 · **Build:** UV + hatchling · **Config:** Pydantic Settings

---

## Overview

`modaltrace` is an OpenTelemetry-native Python observability library purpose-built for
real-time AI avatar and video pipelines. It fills the gap left by general-purpose OTel
libraries (OpenLIT, OpenLLMetry, Logfire) that assume request-response or conversational
patterns and cannot instrument 30fps continuous video workloads without crippling overhead.

The library emits standard OTLP traces, metrics, and logs compatible with any OTel backend
(Grafana, Jaeger, Datadog, Honeycomb, Logfire, Phoenix) with zero vendor lock-in.

---

## Project Structure

```
modaltrace/
│
├── pyproject.toml                  # UV + hatchling, all deps, tool config
├── uv.lock                         # Committed lock file
├── PLAN.md                         # This file
├── README.md
├── CHANGELOG.md
├── LICENSE                         # Apache-2.0
│
├── src/
│   └── modaltrace/
│       │
│       ├── __init__.py             # Full public API surface
│       ├── _version.py             # hatch-vcs generated
│       ├── config.py               # Pydantic Settings — all configuration
│       ├── _registry.py            # Module-level singletons
│       │
│       ├── tracing/
│       │   ├── __init__.py
│       │   ├── pipeline.py         # @pipeline_stage + stage() context manager
│       │   ├── sampler.py          # AdaptiveSampler (time-window + anomaly)
│       │   ├── pending.py          # PendingSpanProcessor (live in-flight spans)
│       │   └── propagation.py      # ThreadPool + ProcessPool context patching
│       │
│       ├── metrics/
│       │   ├── __init__.py
│       │   ├── aggregator.py       # FrameMetricsAggregator (ring buffer + flush)
│       │   ├── instruments.py      # Pre-allocated OTel metric instruments
│       │   └── av_sync.py          # AVSyncTracker (drift + jitter)
│       │
│       ├── logging/
│       │   ├── __init__.py
│       │   ├── api.py              # modaltrace.info/warning/debug/error/span log API
│       │   └── scrubber.py         # PII scrubbing span+log processor
│       │
│       ├── instrumentation/
│       │   ├── __init__.py
│       │   ├── pytorch.py          # wrapt patch of Module.__call__
│       │   ├── gpu.py              # NVML background poller → ObservableGauge
│       │   ├── transport.py        # WebRTC/aiortc stats adapter
│       │   └── eventloop.py        # asyncio event loop lag monitor
│       │
│       ├── conventions/
│       │   ├── __init__.py
│       │   └── attributes.py       # All semantic convention string constants
│       │
│       └── exporters/
│           ├── __init__.py
│           └── setup.py            # OTLP HTTP/gRPC provider setup helpers
│
└── tests/
    ├── conftest.py
    ├── test_pipeline.py
    ├── test_aggregator.py
    ├── test_av_sync.py
    ├── test_pytorch_instrumentation.py
    ├── test_gpu_monitor.py
    ├── test_sampler.py
    ├── test_pending_spans.py
    ├── test_logging_api.py
    ├── test_scrubber.py
    ├── test_propagation.py
    ├── test_eventloop.py
    └── test_transport.py
```

---

## `pyproject.toml` Design

```toml
[build-system]
requires = ["hatchling", "hatch-vcs"]
build-backend = "hatchling.build"

[project]
name = "modaltrace"
dynamic = ["version"]
requires-python = ">=3.10"
description = "OpenTelemetry observability for real-time AI avatar and video pipelines"
license = { text = "Apache-2.0" }

# Core — always installed. No optional heavy deps here.
dependencies = [
    "opentelemetry-api>=1.24.0",
    "opentelemetry-sdk>=1.24.0",
    "opentelemetry-exporter-otlp-proto-http>=1.24.0",
    "opentelemetry-exporter-otlp-proto-grpc>=1.24.0",
    "wrapt>=1.16.0",
    "pydantic>=2.6.0",
    "pydantic-settings>=2.2.0",
]

[project.optional-dependencies]
pytorch = ["torch>=2.0.0"]
gpu     = ["pynvml>=11.5.0"]
webrtc  = ["aiortc>=1.9.0"]
all     = ["modaltrace[pytorch,gpu,webrtc]"]
dev     = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "pytest-mock>=3.12.0",
    "pytest-cov>=5.0.0",
    "ruff>=0.4.0",
    "mypy>=1.9.0",
    "pre-commit>=3.7.0",
]

[tool.uv]
dev-dependencies = ["modaltrace[dev,all]"]

[tool.hatch.version]
source = "vcs"                      # Version from git tags (v0.1.0 → 0.1.0)

[tool.hatch.build.targets.wheel]
packages = ["src/modaltrace"]

[tool.ruff]
line-length = 100
target-version = "py310"
select = ["E", "F", "I", "N", "W", "UP", "B", "C4"]

[tool.mypy]
python_version = "3.10"
strict = false
ignore_missing_imports = true

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
addopts = "--cov=modaltrace --cov-report=term-missing -q"
```

---

## `config.py` — Pydantic Settings Model

Single source of truth for all configuration. Every component reads from this model.
Users can configure via Python kwargs, environment variables (`MODALTRACE_*`), or `.env`.

```python
class ModalTraceConfig(BaseSettings):

    # ── Identity ──────────────────────────────────────────────────────────
    service_name:               str     = "modaltrace-pipeline"
    service_version:            str     = "0.0.0"
    deployment_environment:     str     = "development"

    # ── OTLP Export ───────────────────────────────────────────────────────
    otlp_endpoint:              AnyHttpUrl = "http://localhost:4318"
    otlp_protocol:              Literal["http", "grpc"] = "http"
    otlp_headers:               dict[str, str] = {}
    otlp_timeout_ms:            int     = 10_000

    # ── Feature Flags ─────────────────────────────────────────────────────
    pytorch_instrumentation:    bool    = True
    gpu_monitoring:             bool    = True
    webrtc_monitoring:          bool    = False
    eventloop_monitoring:       bool    = True
    threadpool_propagation:     bool    = True

    # ── Frame Metrics Aggregator ──────────────────────────────────────────
    metrics_flush_interval_ms:  int     = 1_000
    ring_buffer_size:           int     = 512       # Must be power of 2

    # ── Adaptive Sampler ──────────────────────────────────────────────────
    span_window_s:              float   = 1.0       # One stage span per window
    anomaly_threshold_ms:       float   = 50.0      # Always span if slower than this
    pytorch_sample_rate:        float   = 0.01      # Fraction of forward() getting spans

    # ── Pending Spans ─────────────────────────────────────────────────────
    pending_span_flush_interval_ms: int = 5_000     # Export open spans every N ms

    # ── A/V Sync ──────────────────────────────────────────────────────────
    av_drift_warning_ms:        float   = 40.0
    av_chunk_ttl_s:             float   = 5.0
    av_jitter_window:           int     = 30        # Rolling window for jitter calc

    # ── GPU Monitor ───────────────────────────────────────────────────────
    gpu_poll_interval_s:        float   = 1.0
    gpu_device_indices:         list[int] | None = None  # None = all GPUs

    # ── PyTorch Instrumentation ───────────────────────────────────────────
    pytorch_track_memory:       bool    = True
    pytorch_track_shapes:       bool    = False     # Off by default (PII risk)

    # ── PII Scrubbing ─────────────────────────────────────────────────────
    scrubbing_enabled:          bool    = True
    scrubbing_patterns:         list[str] = []      # Extra regex patterns to redact
    scrubbing_callback:         Callable | None = None  # Override per-field

    # ── Structured Logging ────────────────────────────────────────────────
    log_level:                  str     = "info"    # Minimum level to export
    log_console:                bool    = True      # Also print to stdout

    # ── Event Loop Monitor ────────────────────────────────────────────────
    eventloop_lag_threshold_ms: float   = 100.0     # Warn above this block time

    model_config = SettingsConfigDict(
        env_prefix="MODALTRACE_",
        env_file=".env",
        env_file_encoding="utf-8",
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
```

---

## Feature Specifications

---

### 🔴 MUST-HAVE: Pipeline Stage Tracing
**File:** `tracing/pipeline.py`

The core instrumentation primitive. Two interfaces over one implementation.

**Decorator interface:**
```python
@modaltrace.pipeline_stage("flame_inference")
async def run_model(audio: torch.Tensor) -> torch.Tensor:
    return model(audio)

@modaltrace.pipeline_stage("render", always_trace=True)
def render_frame(mesh) -> bytes:
    return renderer.render(mesh)
```

**Context manager interface:**
```python
async with modaltrace.stage("encode", frame_seq=seq_num) as s:
    encoded = encoder.encode(frame)
    s.record("bitrate_kbps", encoder.current_bitrate)
    s.set_attribute("codec", "h264")
```

**Implementation details:**

- `inspect.iscoroutinefunction` called at decoration time, not per-call. Zero runtime branch.
- Yields `StageContext` (not raw OTel span) — stable public interface regardless of OTel SDK upgrades.
- Yields `_NoOpStageContext` when sampler skips — same API, all methods are no-ops, no null checks needed.
- Every span gets `PipelineAttributes.STAGE_NAME`, `PipelineAttributes.SESSION_ID`, `PipelineAttributes.STAGE_DURATION_MS`.
- Exceptions are recorded via `span.record_exception(e)` and re-raised — never swallowed.

**Span hierarchy:**
```
modaltrace.session              ← root, created at init(), long-lived
  └── modaltrace.iteration      ← one per sampler window (~1/sec at 30fps)
        ├── modaltrace.audio_ingest
        ├── modaltrace.flame_inference
        │     └── modaltrace.torch.ARTalkModel   ← from pytorch auto-instrumentation
        ├── modaltrace.render
        └── modaltrace.encode
```

---

### 🔴 MUST-HAVE: Frame Metrics Aggregation
**File:** `metrics/aggregator.py`

Solves the fundamental 30fps overhead problem. OTel calls never happen on the hot path.

**Architecture:**
```
Hot path (render thread):
    FrameMetricsAggregator.record(forward_pass_ms=11.2, render_ms=3.1)
        → lock (~200ns) + array.array write + unlock

Flush thread (daemon, every 1s):
    snapshot = copy buffer under lock
    sort each metric's samples
    histogram.record(value, attrs) for each sample   ← OTel call, off hot path
```

**Data structure:**
- `array.array('d', [0.0] * N)` — typed C float64 array, no GC pressure, no boxing
- Write index via bitmask (`idx & (N-1)`) not modulo — requires `N` to be power of 2 (Pydantic validated)
- Ring buffer overwrites oldest samples on overflow — always has latest N measurements
- Separate `threading.Event` for clean shutdown: `event.wait(timeout)` as sleep, `event.set()` to wake early

**Metrics emitted per flush (as OTel histograms):**

| Metric | Unit | Bucket boundaries |
|---|---|---|
| `modaltrace.inference.forward_pass.duration` | ms | 0.5, 1, 2, 5, 10, 20, 50, 100, 200 |
| `modaltrace.render.frame.duration` | ms | 1, 2, 3, 5, 8, 10, 15, 20, 33, 50 |
| `modaltrace.encode.frame.duration` | ms | 0.5, 1, 2, 5, 10, 20, 50 |
| `modaltrace.audio.chunk.duration` | ms | 1, 2, 5, 10, 20, 50 |
| `modaltrace.av_sync.drift` | ms | -200..200 (signed, custom) |
| `modaltrace.av_sync.jitter` | ms | 0, 1, 2, 5, 10, 20, 50 |
| `modaltrace.pipeline.stage.duration` | ms | 1, 2, 5, 10, 20, 33, 50, 100 |
| `modaltrace.frames.processed` | frames | Counter (no buckets) |
| `modaltrace.frames.dropped` | frames | Counter (no buckets) |

**All instruments pre-allocated in `instruments.py` at `init()` time.** Never created inside loops.

---

### 🔴 MUST-HAVE: PyTorch Auto-Instrumentation
**File:** `instrumentation/pytorch.py`

Instruments every model in the pipeline with zero code changes.

**Patch target:** `torch.nn.Module.__call__` via `wrapt.patch_function_wrapper`.  
Correct target: `__call__` dispatches through hooks before calling `forward()`, capturing total model execution time including hook overhead.

**Two-tier recording:**
```
Every forward() call:
    → record(forward_pass_ms=elapsed) into ring buffer   ← ~200ns, always

1% of calls (or slow outliers >50ms):
    → create full OTel span with model_name, memory_delta, device, shapes   ← ~5µs, rarely
```

**Memory delta:** `torch.cuda.memory_allocated()` before and after call (MB). Positive = cache miss / allocation. Negative = GC freed memory. Catches VRAM leaks across long sessions.

**Shape capture** (`pytorch_track_shapes=False` by default): Extracts `list(tensor.shape)` for all Tensor args. Off by default — in multi-tenant systems, input shapes can reveal user data dimensions.

**Graceful degradation:** `ImportError` on `torch` → `instrument_pytorch()` returns silently. No crash, no warning spam.

**Uninstrumentation:** `uninstrument_pytorch()` restores `torch.nn.Module.__call__.__wrapped__`. Called at `sdk.stop()`. Critical for test isolation.

---

### 🟠 HIGH: A/V Sync Metrics
**File:** `metrics/av_sync.py`

Cross-stage measurement that no existing library provides.

**Measurement model:**
```
audio_captured(chunk_id)     → timestamp_ns recorded at audio capture callback
frame_rendered(chunk_id)     → drift = (render_ts - audio_ts) computed and emitted

Positive drift = video lags audio (most common failure in FLAME pipelines)
Negative drift = video leads audio (over-eager prefetch)
```

**Implementation:**
```python
_pending: dict[int, tuple[int, int]]   # {chunk_id: (capture_ns, expiry_ns)}
_lock: threading.Lock
_drift_window: deque[float]            # last 30 measurements for jitter
```

**Jitter formula:** Mean Absolute Deviation of rolling window — more robust than stddev for real-time signals, more intuitive to interpret ("drift varies by ±X ms on average").

**TTL expiry:** Chunks without a matching frame are cleaned up after `av_chunk_ttl_s` (default 5s). Expired chunks increment `modaltrace.av_sync.unmatched_chunks` counter.

**Warning emission:** When `abs(drift_ms) > av_drift_warning_ms`, emit a structured OTel log event with `modaltrace.av_sync.drift_ms` and `modaltrace.chunk_id` attributes. Surfaces in any OTel log backend.

---

### 🟠 HIGH: One-Liner Init + Backends
**File:** `__init__.py` + `exporters/setup.py`

**Minimal usage:**
```python
import modaltrace
modaltrace.init(service_name="artalk-avatar")
```

**Full usage:**
```python
sdk = modaltrace.init(
    service_name="artalk-avatar",
    otlp_endpoint="http://otel-collector:4318",
    gpu_monitoring=True,
    frame_sample_rate=0.1,
    anomaly_threshold_ms=50.0,
    scrubbing_enabled=True,
    pending_span_flush_interval_ms=5_000,
)
```

**`init()` execution order:**
```
1.  Parse ModalTraceConfig (Pydantic: env vars + kwargs merged + validated)
2.  Set up TracerProvider + BatchSpanProcessor + PendingSpanProcessor → OTLP
3.  Set up MeterProvider + PeriodicExportingMetricReader → OTLP
4.  Set up LoggerProvider + BatchLogRecordProcessor → OTLP
5.  Set global OTel providers
6.  Pre-allocate all metric instruments (histograms, counters, gauges)
7.  Attach PII scrubbing span processor (if scrubbing_enabled)
8.  Start FrameMetricsAggregator flush thread
9.  Start GPUMonitor poll thread (if gpu_monitoring + pynvml available)
10. Call instrument_pytorch() (if pytorch_instrumentation + torch available)
11. Patch ThreadPoolExecutor + ProcessPoolExecutor (if threadpool_propagation)
12. Start asyncio event loop monitor (if eventloop_monitoring)
13. Configure AdaptiveSampler with config values
14. Create root session span
15. Return ModalTraceSDK instance
```

**Backend compatibility (standard OTLP, no plugins needed):**

| Backend | `otlp_endpoint` | Notes |
|---|---|---|
| Grafana + Tempo | `http://tempo:4318` | |
| Jaeger | `http://jaeger:4318` | |
| Datadog | `https://otlp.datadoghq.com` | + `otlp_headers={"DD-API-KEY": "..."}` |
| Honeycomb | `https://api.honeycomb.io` | + `otlp_headers={"x-honeycomb-team": "..."}` |
| New Relic | `https://otlp.nr-data.net` | + `otlp_headers={"api-key": "..."}` |
| Logfire | `https://logfire-api.pydantic.dev` | + `otlp_headers={"Authorization": "..."}` |
| Phoenix (Arize) | `http://phoenix:4317` | + `otlp_protocol="grpc"` |
| Langfuse | `https://otlp.cloud.langfuse.com` | + `otlp_headers={"Authorization": "..."}` |

**SDK return object — context-manager compatible:**
```python
# As context manager (auto-stop on exit):
with modaltrace.init(...) as sdk:
    run_pipeline()

# As object (manual stop):
sdk = modaltrace.init(...)
sdk.av_tracker          # AVSyncTracker
sdk.frame_aggregator    # FrameMetricsAggregator
sdk.stop()              # Flush everything + teardown
```

---

### 🟠 HIGH: GPU Hardware Monitoring
**File:** `instrumentation/gpu.py`

**Poll target:** NVML via `pynvml`. Runs in a daemon `threading.Thread` at `gpu_poll_interval_s`.

**OTel signal:** `ObservableGauge` (not histogram) — GPU metrics are instantaneous state. Callback pattern: SDK calls the callback at export time; `GPUMonitor` returns cached readings from the poll thread.

**Metrics per device (all carry `modaltrace.gpu.device_index` attribute):**

| Metric | Unit | NVML source |
|---|---|---|
| `modaltrace.gpu.utilization` | % | `nvmlDeviceGetUtilizationRates().gpu` |
| `modaltrace.gpu.memory.utilization` | % | `nvmlDeviceGetUtilizationRates().memory` |
| `modaltrace.gpu.memory.used` | MB | `nvmlDeviceGetMemoryInfo().used` |
| `modaltrace.gpu.memory.free` | MB | `nvmlDeviceGetMemoryInfo().free` |
| `modaltrace.gpu.memory.total` | MB | `nvmlDeviceGetMemoryInfo().total` |
| `modaltrace.gpu.temperature` | °C | `nvmlDeviceGetTemperature(NVML_TEMPERATURE_GPU)` |
| `modaltrace.gpu.power.draw` | W | `nvmlDeviceGetPowerUsage() / 1000` |

**Three failure modes handled silently:** `pynvml` not installed, no NVIDIA GPU present, individual metric unavailable (some GPUs don't expose power draw).

**Complements PyTorch memory tracking:** NVML shows total GPU memory including CUDA runtime and other processes. `torch.cuda.memory_allocated()` shows only PyTorch tensors in this process. Both are needed.

---

### 🟠 HIGH: Pending Span Processor (NEW — from Logfire gap analysis)
**File:** `tracing/pending.py`

**Problem:** Without this, the `modaltrace.session` root span (which lives for the entire avatar session) is invisible to the backend until `sdk.stop()` is called. A 10-minute avatar session appears as 10 minutes of silence followed by a burst of data.

**Solution:** `PendingSpanProcessor` exports a snapshot of every open (not-yet-ended) span at a configurable interval. Inspired directly by Logfire's implementation.

**Implementation:**
```python
class PendingSpanProcessor(SpanProcessor):
    """
    Exports a snapshot of all currently-open spans at a fixed interval.
    The snapshot is a copy with the current timestamp as an artificial end_time,
    marked with `modaltrace.span.pending = True` so backends can distinguish
    pending snapshots from completed spans.
    """

    def __init__(self, exporter: SpanExporter, flush_interval_ms: int = 5_000):
        self._exporter = exporter
        self._interval_s = flush_interval_ms / 1000.0
        self._open_spans: dict[int, ReadableSpan] = {}   # span_id → span
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._flush_loop, daemon=True)

    def on_start(self, span, parent_context):
        with self._lock:
            self._open_spans[span.context.span_id] = span

    def on_end(self, span):
        with self._lock:
            self._open_spans.pop(span.context.span_id, None)
        # Normal export of completed span handled by BatchSpanProcessor

    def _flush_loop(self):
        while not self._stop.wait(timeout=self._interval_s):
            self._export_pending()

    def _export_pending(self):
        with self._lock:
            open_spans = list(self._open_spans.values())
        if not open_spans:
            return
        # Build snapshot copies with artificial end_time = now
        now_ns = time.time_ns()
        snapshots = []
        for span in open_spans:
            snapshot = _make_pending_snapshot(span, now_ns)
            snapshots.append(snapshot)
        self._exporter.export(snapshots)
```

**Backend rendering:** The `modaltrace.span.pending = True` attribute tells the UI to render these with a different color/style (dashed border in Grafana, "in progress" badge in Datadog). Any backend that doesn't understand this attribute simply shows them as normal spans with short durations, which is still useful.

**Flush interval config:** `pending_span_flush_interval_ms = 5_000` (default 5s). Shorter = more real-time visibility, more export overhead. 5s is a good production default.

---

### 🟠 HIGH: Structured Log API (NEW — from Logfire gap analysis)
**File:** `logging/api.py`

**Problem:** `modaltrace` was trace-and-metrics only. Users who want to emit pipeline events (warnings, errors, info about pipeline state) had to use Python's `logging` stdlib separately, losing OTel context propagation and structured attribute extraction.

**Public API:**
```python
modaltrace.info("Pipeline started", session_id=session_id, target_fps=30)
modaltrace.debug("FLAME params computed", param_count=236, drift_ms=-2.4)
modaltrace.warning("A/V drift threshold exceeded", drift_ms=47.3, chunk_id=1024)
modaltrace.error("GPU OOM during render", model_name="ARTalk", batch_size=4)
modaltrace.exception("Unhandled error in pipeline stage", stage="encode")
```

**All kwargs become structured OTel log record attributes** — queryable in any OTel log backend.

**f-string template support** (like Logfire):
```python
chunk_id = 42
drift = 47.3
modaltrace.warning("A/V drift exceeded on chunk {chunk_id}", chunk_id=chunk_id, drift_ms=drift)
# span_name = "A/V drift exceeded on chunk {chunk_id}"  (queryable, consistent)
# message   = "A/V drift exceeded on chunk 42"           (human-readable)
# attributes: chunk_id=42, drift_ms=47.3
```

**Implementation on top of OTel Logs API:**
- `LoggerProvider` set up during `init()` alongside `TracerProvider` and `MeterProvider`
- `modaltrace.info(msg, **attrs)` calls `otel_logger.emit(LogRecord(body=msg, attributes=attrs, severity=INFO))`
- Each log record carries the current OTel trace context (`trace_id`, `span_id`) automatically — logs are correlated to the active span without any manual plumbing
- `log_console=True` (default) also prints to stdout with indentation matching active span depth

**Level filtering:** `log_level` config (default `"info"`) filters at emit time. `DEBUG` logs in dev, `INFO` in staging, `WARNING` in production.

---

### 🟠 MEDIUM: ThreadPool Context Propagation (NEW — from Logfire gap analysis)
**File:** `tracing/propagation.py`

**Problem:** When pipeline stages offload work to a `ThreadPoolExecutor` (common for CPU-bound rendering), spans created in worker threads have no OTel parent — they appear as disconnected root spans in the trace view.

**Solution:** Patch `ThreadPoolExecutor.submit` and `ProcessPoolExecutor.submit` to capture the current OTel context and attach it inside the worker before execution.

```python
def patch_thread_pool_executor():
    """
    Patch ThreadPoolExecutor.submit to propagate OTel context into workers.
    Called once during init() if threadpool_propagation=True.
    """
    import wrapt
    from opentelemetry import context as otel_context

    @wrapt.patch_function_wrapper("concurrent.futures", "ThreadPoolExecutor.submit")
    def patched_submit(wrapped, instance, args, kwargs):
        fn, *fn_args = args
        current_ctx = otel_context.get_current()

        def wrapped_fn(*a, **kw):
            token = otel_context.attach(current_ctx)
            try:
                return fn(*a, **kw)
            finally:
                otel_context.detach(token)

        return wrapped(wrapped_fn, *fn_args, **kwargs)
```

**ProcessPoolExecutor** is also patched, but context is serialized via `pickle`. If pickling fails (e.g., lambda callbacks), the patch logs a warning and falls back to no-op — the pipeline continues running, just without context propagation in that worker.

**Scope:** Only patched if `threadpool_propagation=True` (default). Users who manage context manually can disable it.

---

### 🟠 MEDIUM: PII Scrubbing (NEW — from Logfire gap analysis)
**File:** `logging/scrubber.py`

**Problem:** Avatar pipelines process user audio and potentially face data. Span attributes like `audio_chunk_content`, `user_id`, or even `input_shapes` (which can reveal image resolution = user identity hint) can contain or imply sensitive information.

**Implementation:** A `SpanProcessor` and `LogRecordProcessor` that scan all string-valued attributes before export, redacting values that match configured patterns.

```python
DEFAULT_SCRUB_PATTERNS = [
    r"password",
    r"token",
    r"secret",
    r"api[_-]?key",
    r"authorization",
    r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b",  # Credit card
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",  # Email
    r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b",              # Phone number
]

class ScrubbingSpanProcessor(SpanProcessor):
    """
    Scans span attributes before export and redacts values matching
    sensitive patterns. Runs as a span processor in the chain so
    scrubbing happens before any exporter sees the data.

    A scrubbing_callback can inspect each match and return the original
    value to allow-list known-safe attributes.
    """

    def on_end(self, span: ReadableSpan):
        for key, value in span.attributes.items():
            if isinstance(value, str):
                for pattern in self._compiled_patterns:
                    if pattern.search(key) or pattern.search(value):
                        # Check callback allow-list first
                        if self._callback and self._callback(key, value, pattern):
                            continue
                        span._attributes[key] = "[REDACTED]"
                        break
```

**Scrubbing callback** for custom allow-listing:
```python
def my_callback(key: str, value: str, pattern) -> bool:
    # Return True to KEEP the value (override redaction)
    if key == "model_name":
        return True   # model names contain "secret" sometimes but aren't PII
    return False

modaltrace.init(scrubbing_callback=my_callback)
```

**Key design:** Scrubbing happens in `on_end` (after span is complete), not on attribute write. This avoids overhead on the hot path. The span processor runs before the `BatchSpanProcessor` in the chain.

---

### 🟡 MEDIUM: Adaptive Sampling
**File:** `tracing/sampler.py`

**Three-tier decision (evaluated in order):**
```
1. FORCE    → always_trace=True on the decorator → always create span
2. ANOMALY  → elapsed_ms > anomaly_threshold_ms → always create span
3. WINDOW   → has a span been created for this stage in the last window_s? → if not, create
```

**State:**
```python
_last_span_time: dict[str, float]   # stage_name → last span creation timestamp
_lock: threading.Lock               # held for ~50ns (dict lookup + write)
```

**Anomaly detection** runs in the finally block of every instrumented call — after the call completes, elapsed is known. If the call was slow, the span would already be created (because spans must be created at call START, not end). The anomaly trigger therefore only works for the **next** call from the same stage — or the sampler can create a synthetic "anomaly event" log record instead of a span.

**Why not OTel's built-in samplers:**  
`TraceIdRatioBased` uses request-level random sampling — meaningless for a continuous pipeline with no "requests". Time-window sampling guarantees at least one span per stage per second regardless of call rate.

---

### 🟡 LOW: Asyncio Event Loop Monitoring (NEW — from Logfire gap analysis)
**File:** `instrumentation/eventloop.py`

**Problem:** In async avatar pipelines, a slow synchronous render call blocking the event loop for >100ms delays audio processing, causing A/V drift that looks like a model problem but is actually an async scheduling problem.

**Implementation:** Patch `asyncio.events.Handle._run` to measure its own execution time. Emit a structured log event when it exceeds the threshold.

```python
def install_eventloop_monitor(threshold_ms: float = 100.0):
    """
    Patch asyncio.events.Handle._run to detect event loop blocking.
    Emits modaltrace.warning() when a handle blocks longer than threshold_ms.
    """
    import asyncio
    original_run = asyncio.events.Handle._run

    def patched_run(self):
        start = time.perf_counter()
        try:
            original_run(self)
        finally:
            elapsed_ms = (time.perf_counter() - start) * 1000
            if elapsed_ms > threshold_ms:
                # Use the structured log API to emit the warning
                modaltrace.warning(
                    "Event loop blocked for {elapsed_ms:.1f}ms",
                    elapsed_ms=elapsed_ms,
                    threshold_ms=threshold_ms,
                    handle_callback=getattr(self._callback, "__qualname__", str(self._callback)),
                )

    asyncio.events.Handle._run = patched_run
```

**Config:** `eventloop_lag_threshold_ms = 100.0` (default). Logs a warning on every handle that blocks longer than this. Set higher (e.g., 500ms) in production to reduce noise, lower (e.g., 10ms) in development to catch subtle blocks.

**Integration with A/V sync:** Event loop lag events are automatically correlated to the active trace context (if any), so you can query "show me all A/V drift events that were preceded by an event loop lag event within 100ms" in any SQL-capable backend.

---

### 🟡 LOW: WebRTC / Transport Metrics
**File:** `instrumentation/transport.py`

**Requires:** `modaltrace[webrtc]` extra. Must be explicitly started — never auto-instruments.

**Usage:**
```python
from modaltrace.instrumentation.transport import WebRTCMetricsAdapter
adapter = WebRTCMetricsAdapter(peer_connection, poll_interval_s=2.0)
adapter.start()
```

**Stats collection:** Polls `aiortc.RTCPeerConnection.getStats()` as an asyncio Task. Filters by `report.type`:

| Report type | Metrics extracted |
|---|---|
| `outbound-rtp` | `frames_sent`, `bytes_sent`, `frames_per_second`, derived `bitrate_kbps` |
| `remote-inbound-rtp` | `round_trip_time`, `jitter`, `packets_lost`, derived `packet_loss_percent` |
| `candidate-pair` (succeeded) | `current_round_trip_time` (ICE-level RTT) |

**OTel metrics emitted:**

| Metric | Unit |
|---|---|
| `modaltrace.transport.rtt` | ms |
| `modaltrace.transport.jitter` | ms |
| `modaltrace.transport.packet_loss` | % |
| `modaltrace.transport.frame_rate` | fps |
| `modaltrace.transport.bitrate` | kbps |

All carry `modaltrace.transport.protocol="webrtc"` and `modaltrace.transport.stream` ("audio"/"video") attributes.

---

## Semantic Conventions
**File:** `conventions/attributes.py`

All string constants in one place — zero magic strings in the rest of the codebase.

```python
class PipelineAttributes:
    ID                = "modaltrace.pipeline.id"
    SESSION_ID        = "modaltrace.pipeline.session_id"
    STAGE_NAME        = "modaltrace.pipeline.stage.name"
    STAGE_DURATION_MS = "modaltrace.pipeline.stage.duration_ms"
    FRAME_SEQ         = "modaltrace.pipeline.frame.sequence_number"
    TARGET_FPS        = "modaltrace.pipeline.target_fps"
    SPAN_PENDING      = "modaltrace.span.pending"       # True for PendingSpanProcessor snapshots

class InferenceAttributes:
    MODEL_NAME              = "modaltrace.inference.model_name"
    FORWARD_PASS_MS         = "modaltrace.inference.forward_pass_ms"
    BATCH_SIZE              = "modaltrace.inference.batch_size"
    GPU_MEMORY_MB           = "modaltrace.inference.gpu.memory_allocated_mb"
    GPU_MEMORY_DELTA_MB     = "modaltrace.inference.gpu.memory_delta_mb"
    INPUT_SHAPES            = "modaltrace.inference.input_shapes"
    DEVICE                  = "modaltrace.inference.device"

class ModalAttributes:
    FLAME_INFERENCE_MS      = "modaltrace.flame.inference_ms"
    FLAME_PARAM_COUNT       = "modaltrace.flame.parameter_count"
    RENDER_FRAME_MS         = "modaltrace.render.frame_ms"
    RENDER_RESOLUTION       = "modaltrace.render.resolution"
    MESH_VERTEX_COUNT       = "modaltrace.mesh.vertex_count"
    FRAME_SEQ               = "modaltrace.frame.sequence_number"

class AVSyncAttributes:
    DRIFT_MS                = "modaltrace.av_sync.drift_ms"
    JITTER_MS               = "modaltrace.av_sync.jitter_ms"
    THRESHOLD_MS            = "modaltrace.av_sync.threshold_ms"
    UNMATCHED_CHUNKS        = "modaltrace.av_sync.unmatched_chunks"
    CHUNK_ID                = "modaltrace.av_sync.chunk_id"

class GPUAttributes:
    DEVICE_INDEX            = "modaltrace.gpu.device_index"
    UTILIZATION_PCT         = "modaltrace.gpu.utilization"
    MEMORY_USED_MB          = "modaltrace.gpu.memory.used"
    MEMORY_FREE_MB          = "modaltrace.gpu.memory.free"
    TEMPERATURE_C           = "modaltrace.gpu.temperature"
    POWER_W                 = "modaltrace.gpu.power.draw"

class TransportAttributes:
    PROTOCOL                = "modaltrace.transport.protocol"
    RTT_MS                  = "modaltrace.transport.rtt_ms"
    JITTER_MS               = "modaltrace.transport.jitter_ms"
    PACKET_LOSS_PCT         = "modaltrace.transport.packet_loss_percent"
    BITRATE_KBPS            = "modaltrace.transport.bitrate_kbps"
    FRAME_RATE_ACTUAL       = "modaltrace.transport.frame_rate_actual"
    STREAM                  = "modaltrace.transport.stream"

class EventLoopAttributes:
    ELAPSED_MS              = "modaltrace.eventloop.blocked_ms"
    THRESHOLD_MS            = "modaltrace.eventloop.threshold_ms"
    HANDLE_CALLBACK         = "modaltrace.eventloop.handle_callback"
```

---

## Public API Surface
**File:** `__init__.py`

Everything a user needs is importable from `modaltrace` directly:

```python
import modaltrace

# Init
sdk = modaltrace.init(...)

# Tracing
@modaltrace.pipeline_stage("flame_inference")
async def run_model(...): ...

async with modaltrace.stage("render") as s:
    s.record("vertex_count", 12345)

# Structured logging
modaltrace.trace("Trace level message", key=value)
modaltrace.debug("Debug message", key=value)
modaltrace.info("Info message", key=value)
modaltrace.notice("Notice message", key=value)
modaltrace.warning("Warning message", key=value)
modaltrace.error("Error message", key=value)
modaltrace.exception("Exception message")       # captures current exception

# A/V sync
av = sdk.av_tracker
av.audio_captured(chunk_id=42)
av.frame_rendered(chunk_id=42)
av.current_drift_ms                              # property

# Frame metrics
agg = sdk.frame_aggregator
agg.record(forward_pass_ms=11.2, render_ms=3.1)

# Accessors
sdk.stop()
sdk.flush()                                      # Force-flush all exporters
```

---

## End-to-End Example

```python
import torch
import modaltrace

# 1. One-liner init — all features enabled by default
sdk = modaltrace.init(
    service_name="artalk-avatar",
    otlp_endpoint="http://localhost:4318",
    gpu_monitoring=True,
    pending_span_flush_interval_ms=5_000,
    scrubbing_enabled=True,
    av_drift_warning_ms=40.0,
)

# 2. PyTorch models — automatically instrumented, zero code changes
artalk = ARTalkModel().cuda()
flame  = FLAMEDecoder().cuda()

# 3. Structured logging — correlated to active span automatically
modaltrace.info("Pipeline initialised", model="artalk", device="cuda:0")

# 4. Decorator-based pipeline stages
@modaltrace.pipeline_stage("audio_ingest")
async def ingest_audio(raw: bytes) -> torch.Tensor:
    return torch.frombuffer(raw, dtype=torch.float32).cuda()

@modaltrace.pipeline_stage("flame_inference")
async def run_flame(audio: torch.Tensor) -> torch.Tensor:
    return artalk(audio)   # auto-instrumented by pytorch patch

@modaltrace.pipeline_stage("render")
async def render(params: torch.Tensor) -> bytes:
    async with modaltrace.stage("mesh_deform") as s:
        mesh = flame(params)
        s.record("vertex_count", mesh.vertices.shape[0])
    return renderer.render(mesh)

# 5. A/V sync tracking
av = sdk.av_tracker

async def process_chunk(chunk_id: int, audio: bytes) -> bytes:
    av.audio_captured(chunk_id)                  # timestamp at entry

    tensor  = await ingest_audio(audio)
    params  = await run_flame(tensor)
    frame   = await render(params)

    av.frame_rendered(chunk_id)                  # drift computed here

    # Frame metrics: ring buffer write, ~200ns
    sdk.frame_aggregator.record(
        forward_pass_ms=artalk.last_forward_ms,
        render_ms=renderer.last_render_ms,
    )
    return frame
```

---

## Performance Budget

| Component | Per-frame overhead | Notes |
|---|---|---|
| `FrameMetricsAggregator.record()` | ~200 ns | Lock + bitmask + array write |
| `AVSyncTracker.audio_captured()` | ~300 ns | Lock + dict insert |
| `AVSyncTracker.frame_rendered()` | ~500 ns | Lock + drift compute |
| `AdaptiveSampler.should_sample()` | ~100 ns | Lock + dict lookup |
| PyTorch `perf_counter_ns()` calls | ~100 ns | Two calls per forward() |
| PendingSpanProcessor (amortised) | ~50 ns | Flush every 5s, cost spread |
| Scrubber (amortised) | ~20 ns | Runs on span end, not per-frame |
| Event loop monitor | ~150 ns | Two perf_counter calls per handle |
| Span creation (when sampled, 1%) | ~5–10 µs | Amortised over ~100 frames |
| **Total (no span created)** | **~1.4 µs** | 0.004% of 33ms frame budget |
| **Total (with span, amortised)** | **~1.5 µs** | Negligible |

At 30fps the frame budget is 33.3ms. Total instrumentation overhead is under 2 microseconds per frame.

---

## Testing Strategy

**Framework:** `pytest` + `pytest-asyncio` + `pytest-mock` + `pytest-cov`  
**Target:** 100% line coverage on all non-instrumentation modules. Instrumentation modules tested with mocked `torch`/`pynvml`.

| Test file | What it validates |
|---|---|
| `test_pipeline.py` | Span creation, hierarchy, async/sync decorator, NoOp when sampled |
| `test_aggregator.py` | Ring buffer correctness, flush timing, histogram emission |
| `test_av_sync.py` | Drift formula, jitter, TTL expiry, warning emission |
| `test_pytorch_instrumentation.py` | wrapt patch applied/removed, memory delta, shape capture |
| `test_gpu_monitor.py` | NVML polling, ObservableGauge callbacks, graceful degradation |
| `test_sampler.py` | Time-window logic, anomaly override, always_trace override |
| `test_pending_spans.py` | Snapshot creation, pending attribute, flush interval |
| `test_logging_api.py` | Structured attributes, level filtering, trace context correlation |
| `test_scrubber.py` | Pattern matching, redaction, callback allow-list |
| `test_propagation.py` | ThreadPool context carry-through, ProcessPool pickle failure |
| `test_eventloop.py` | Handle patch applied, lag detection, warning emitted |
| `test_transport.py` | WebRTC stats parsing, metric emission, graceful degradation |

**CI matrix:** Python 3.10 / 3.11 / 3.12 on every PR. PyTorch integration tests on push to `main` only (download size).

---

## Build and Release

**Versioning:** `hatch-vcs` reads from git tags. `git tag v0.1.0 && git push origin v0.1.0` → CI publishes to PyPI.

**Release command:**
```bash
uv build
uv publish   # reads UV_PUBLISH_TOKEN from env
```

**Pre-commit hooks (`.pre-commit-config.yaml`):**
```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    hooks:
      - id: ruff          # lint + autofix
      - id: ruff-format   # formatting
  - repo: https://github.com/pre-commit/mirrors-mypy
    hooks:
      - id: mypy
```

No `black`, no `isort`, no `flake8` — `ruff` replaces all three.

---

## Implementation Phases

| Phase | Deliverable | Validates |
|---|---|---|
| 1 | `conventions/attributes.py` + `config.py` | All names and config contract defined first |
| 2 | `metrics/instruments.py` + `metrics/aggregator.py` | Ring buffer correctness, flush timing |
| 3 | `tracing/sampler.py` + `tracing/pipeline.py` | Span creation, hierarchy, async/sync |
| 4 | `tracing/pending.py` | PendingSpanProcessor, in-flight visibility |
| 5 | `logging/api.py` | Structured log API, trace context correlation |
| 6 | `logging/scrubber.py` | PII scrubbing pipeline |
| 7 | `instrumentation/pytorch.py` | wrapt patch, memory delta, shape capture |
| 8 | `metrics/av_sync.py` | Drift formula, jitter, TTL |
| 9 | `instrumentation/gpu.py` | NVML polling, ObservableGauge callbacks |
| 10 | `tracing/propagation.py` | ThreadPool + ProcessPool context carry |
| 11 | `instrumentation/eventloop.py` | asyncio lag detection |
| 12 | `__init__.py` + `exporters/setup.py` | Full init() integration test |
| 13 | `instrumentation/transport.py` | WebRTC adapter |
| 14 | Packaging, CI, README | PyPI publish dry run |
