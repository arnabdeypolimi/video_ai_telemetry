# ModalTrace API Reference

## Core Classes

### ModalTraceConfig

Configuration class for ModalTrace SDK. Uses Pydantic Settings for validation.

```python
from modaltrace import ModalTraceConfig

config = ModalTraceConfig(
    service_name="my-pipeline",
    service_version="1.0.0",
    deployment_environment="production",
    otlp_endpoint="http://localhost:4318",
    pytorch_instrumentation=True,
    gpu_monitoring=True
)
```

#### Parameters

**Service Identity:**
- `service_name` (str, default: "modaltrace-pipeline") - Service identifier
- `service_version` (str, default: "0.0.0") - Semantic version
- `deployment_environment` (str, default: "development") - Environment name

**OTLP Export:**
- `otlp_endpoint` (URL, default: "http://localhost:4318") - Collector endpoint
- `otlp_protocol` (str, default: "http") - Protocol: "http" or "grpc"
- `otlp_headers` (dict, default: {}) - Custom headers
- `otlp_timeout_ms` (int, default: 10000) - Export timeout

**Feature Flags:**
- `pytorch_instrumentation` (bool, default: True) - Enable PyTorch instrumentation
- `gpu_monitoring` (bool, default: True) - Enable GPU monitoring
- `webrtc_monitoring` (bool, default: False) - Enable WebRTC monitoring
- `eventloop_monitoring` (bool, default: True) - Enable event loop monitoring

**Sampling:**
- `pytorch_sample_rate` (float, default: 0.01) - PyTorch sample rate (0-1)
- `anomaly_threshold_ms` (float, default: 50.0) - Anomaly detection threshold
- `span_window_s` (float, default: 1.0) - Sampling window in seconds

**Metrics:**
- `metrics_flush_interval_ms` (int, default: 1000) - Flush interval
- `ring_buffer_size` (int, default: 512) - Buffer size (power of 2)

**Audio/Video Sync:**
- `av_drift_warning_ms` (float, default: 40.0) - Drift warning threshold
- `av_chunk_ttl_s` (float, default: 5.0) - Chunk TTL in seconds
- `av_jitter_window` (int, default: 30) - Jitter window size

**GPU Monitoring:**
- `gpu_poll_interval_s` (float, default: 1.0) - Poll interval
- `gpu_device_indices` (list[int], optional) - Specific GPUs to monitor

**PII Scrubbing:**
- `scrubbing_enabled` (bool, default: True) - Enable scrubbing
- `scrubbing_patterns` (list[str], default: []) - Regex patterns to scrub
- `scrubbing_callback` (callable, optional) - Custom scrubbing function

**Logging:**
- `log_level` (str, default: "info") - Log level
- `log_console` (bool, default: True) - Console output

### ModalTraceSDK

Main SDK class for managing telemetry.

```python
from modaltrace import ModalTraceSDK

sdk = ModalTraceSDK()
sdk.start()

# ... your application code ...

sdk.shutdown()
```

#### Methods

```python
def start() -> None:
    """Initialize and start the SDK."""

def shutdown(timeout_ms: int = 30000) -> None:
    """Shutdown the SDK and flush pending telemetry."""

def get_tracer(name: str) -> Tracer:
    """Get a tracer instance."""

def get_meter(name: str) -> Meter:
    """Get a meter instance."""

def get_logger(name: str) -> Logger:
    """Get a logger instance."""
```

## Tracing API

### Tracer

OpenTelemetry tracer for creating spans.

```python
from modaltrace import get_tracer

tracer = get_tracer(__name__)

with tracer.start_as_current_span("operation_name") as span:
    span.set_attribute("key", "value")
    # Your code here
```

#### Methods

```python
def start_as_current_span(name: str) -> Span:
    """Create and activate a span."""

def start_span(name: str) -> Span:
    """Create a span without activating it."""
```

### Span

Represents a unit of work.

```python
span.set_attribute("modaltrace.pipeline.frame.sequence_number", 42)
span.add_event("frame_processed", attributes={"fps": 30})
span.record_exception(exception)
span.set_status(Status(StatusCode.OK))
```

#### Methods

```python
def set_attribute(key: str, value: Any) -> None:
    """Set a span attribute."""

def add_event(name: str, attributes: dict = None, timestamp: int = None) -> None:
    """Add an event to the span."""

def record_exception(exception: Exception, attributes: dict = None) -> None:
    """Record an exception in the span."""

def set_status(status: Status) -> None:
    """Set the span status."""
```

## Metrics API

### Meter

Factory for creating metric instruments.

```python
from modaltrace.metrics import get_meter

meter = get_meter(__name__)
```

#### Methods

```python
def create_histogram(name: str, unit: str = "", description: str = "") -> Histogram:
    """Create a histogram instrument."""

def create_counter(name: str, unit: str = "", description: str = "") -> Counter:
    """Create a counter instrument."""

def create_gauge(name: str, unit: str = "", description: str = "") -> Gauge:
    """Create a gauge instrument."""
```

### Instruments

```python
# Histogram
histogram = meter.create_histogram("inference.latency", unit="ms")
histogram.record(12.5)

# Counter
counter = meter.create_counter("frames.processed")
counter.add(1)

# Gauge
gauge = meter.create_gauge("gpu.memory", unit="MB")
gauge.set(4096)
```

## Logging API

### Structured Logging

```python
from modaltrace.logging import info, error, warning, debug

info("Processing frame", frame_id=42, fps=30)
error("Inference failed", error_code=500)
warning("GPU temperature high", temperature_c=85)
debug("Internal state", state={"queue_size": 10})
```

#### Functions

```python
def info(message: str, **kwargs) -> None:
    """Log info level message with context."""

def error(message: str, **kwargs) -> None:
    """Log error level message with context."""

def warning(message: str, **kwargs) -> None:
    """Log warning level message with context."""

def debug(message: str, **kwargs) -> None:
    """Log debug level message with context."""
```

## Semantic Conventions

### Attribute Constants

```python
from modaltrace.conventions.attributes import (
    PipelineAttributes,
    InferenceAttributes,
    ModalAttributes,
    AVSyncAttributes,
    GPUAttributes,
    TransportAttributes,
    EventLoopAttributes,
)

# Pipeline
span.set_attribute(PipelineAttributes.FRAME_SEQ, 0)
span.set_attribute(PipelineAttributes.TARGET_FPS, 30)

# Inference
span.set_attribute(InferenceAttributes.MODEL_NAME, "my-model")
span.set_attribute(InferenceAttributes.FORWARD_PASS_MS, 11.5)

# GPU
span.set_attribute(GPUAttributes.DEVICE_INDEX, 0)
span.set_attribute(GPUAttributes.MEMORY_USED_MB, 2048)

# A/V Sync
span.set_attribute(AVSyncAttributes.DRIFT_MS, 5.2)
span.set_attribute(AVSyncAttributes.JITTER_MS, 2.1)
```

## Advanced Usage

### Custom Span Processor

```python
from opentelemetry.sdk.trace import SpanProcessor
from opentelemetry.trace import Span

class CustomProcessor(SpanProcessor):
    def on_start(self, span: Span, parent_context) -> None:
        print(f"Span started: {span.name}")

    def on_end(self, span: Span) -> None:
        print(f"Span ended: {span.name}")

    def shutdown(self) -> None:
        pass

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        return True

# Register processor
from opentelemetry import trace
trace.get_tracer_provider().add_span_processor(CustomProcessor())
```

### PII Scrubbing

```python
from modaltrace import ModalTraceConfig

# Built-in patterns
config = ModalTraceConfig(
    scrubbing_enabled=True,
    scrubbing_patterns=[
        r'\b\d{3}-\d{2}-\d{4}\b',  # SSN
        r'\b\d{16}\b',               # Credit card
    ]
)

# Custom callback
def custom_scrubber(value):
    if isinstance(value, str) and len(value) > 50:
        return value[:10] + "***REDACTED***"
    return value

config = ModalTraceConfig(
    scrubbing_callback=custom_scrubber
)
```

### Context Propagation

```python
from modaltrace.tracing.propagation import propagate_context
from concurrent.futures import ThreadPoolExecutor

def worker(task_id):
    # Context automatically propagated
    tracer = get_tracer(__name__)
    with tracer.start_as_current_span(f"task_{task_id}"):
        # Your work here
        pass

with ThreadPoolExecutor() as executor:
    futures = []
    for i in range(10):
        future = executor.submit(propagate_context(worker), i)
        futures.append(future)
```

## Error Handling

```python
from opentelemetry.trace import Status, StatusCode

try:
    with tracer.start_as_current_span("risky_operation") as span:
        # Code that might fail
        result = risky_function()
        span.set_status(Status(StatusCode.OK))
except Exception as e:
    span.record_exception(e)
    span.set_status(Status(StatusCode.ERROR, description=str(e)))
    raise
```

## Configuration from Environment

```bash
# Set via environment variables
export MODALTRACE_SERVICE_NAME=my-app
export MODALTRACE_OTLP_ENDPOINT=http://collector:4318
export MODALTRACE_PYTORCH_INSTRUMENTATION=true
export MODALTRACE_GPU_MONITORING=true
```

```python
# Load from environment
from modaltrace import ModalTraceConfig

config = ModalTraceConfig()  # Reads from MODALTRACE_* env vars
```

## Dashboard API Endpoints

The optional ModalTrace dashboard provides REST API endpoints for querying telemetry data. The dashboard server receives OTLP data on port 4318 and serves APIs and static files on port 8000.

### OTLP Receiver Endpoints

These endpoints accept OTLP protobuf messages:

```
POST /v1/traces       # Receive trace data
POST /v1/metrics      # Receive metrics data
POST /v1/logs         # Receive logs data
```

### Query Endpoints

#### Spans

```
GET /api/spans?since_ms=<timestamp>&limit=50
```

Returns list of recent spans (newest first).

**Response:**
```json
[
  {
    "trace_id": "abc123...",
    "span_id": "def456...",
    "name": "process_frame",
    "service_name": "my-pipeline",
    "start_time_ms": 1234567890,
    "duration_ms": 45.3,
    "status": "OK",
    "attributes": {
      "modaltrace.pipeline.frame.sequence_number": 42
    }
  }
]
```

#### Metrics

```
GET /api/metrics/{name}?since_ms=<timestamp>
```

Returns time series data for a specific metric.

**Examples:**
- `/api/metrics/modaltrace.pipeline.stage.duration?since_ms=1234567890`
- `/api/metrics/modaltrace.frames.dropped`
- `/api/metrics/modaltrace.av_sync.drift`

**Response:**
```json
[
  {
    "name": "modaltrace.pipeline.stage.duration",
    "value": 45.3,
    "timestamp_ms": 1234567890,
    "attributes": {
      "modaltrace.pipeline.stage": "inference"
    },
    "percentiles": {
      "p50": 40.0,
      "p95": 45.3,
      "p99": 50.0
    }
  }
]
```

#### GPU Metrics

```
GET /api/gpu
```

Returns latest GPU readings grouped by device.

**Response:**
```json
{
  "0": {
    "device_index": 0,
    "modaltrace.gpu.utilization": 0.75,
    "modaltrace.gpu.memory.used": 8.2,
    "modaltrace.gpu.memory.total": 24,
    "modaltrace.gpu.temperature": 72,
    "modaltrace.gpu.power.draw": 210
  }
}
```

#### Logs

```
GET /api/logs?since_ms=<timestamp>&level=<ERROR|WARN|INFO>&limit=100
```

Returns recent log records (newest first).

**Response:**
```json
[
  {
    "timestamp_ms": 1234567890,
    "severity": "ERROR",
    "body": "GPU memory allocation failed",
    "trace_id": "abc123...",
    "span_id": "def456...",
    "attributes": {
      "error.code": 500
    }
  }
]
```

### Static Files

```
GET /             # Served from src/modaltrace/dashboard/static/
```

Returns the dashboard web UI.

### Dashboard Usage

**Start the dashboard server:**

```python
from modaltrace.dashboard import DashboardServer

server = DashboardServer()
server.start()  # Listens on port 8000 (dashboard) and 4318 (OTLP)
```

**Configure your application to send telemetry:**

```python
from modaltrace import ModalTraceConfig, ModalTraceSDK

config = ModalTraceConfig(
    service_name="my-pipeline",
    otlp_endpoint="http://localhost:4318",  # Send to dashboard
    otlp_protocol="http"
)

sdk = ModalTraceSDK(config)
sdk.start()
```

**View dashboard:**

Open `http://localhost:8000` in your browser to see real-time telemetry.

### Dashboard Telemetry Requirements

For proper dashboard visualization, ensure your telemetry includes:

#### Required Metrics

- `modaltrace.pipeline.stage.duration` with `modaltrace.pipeline.stage` attribute (inference, render, encode)
- `modaltrace.frames.dropped` counter
- `modaltrace.av_sync.drift` gauge

#### Optional GPU Metrics

- `modaltrace.gpu.utilization` (0-1 range)
- `modaltrace.gpu.memory.used` (GB)
- `modaltrace.gpu.memory.total` (GB)
- `modaltrace.gpu.temperature` (°C)
- `modaltrace.gpu.power.draw` (W)

#### Span Attributes

Include semantic attributes for better filtering:
- `modaltrace.pipeline.frame.sequence_number`
- `modaltrace.pipeline.stage` (inference, render, encode)
- `modaltrace.inference.model.name`
- `modaltrace.gpu.device_index`

---

For more examples, see [EXAMPLES.md](./EXAMPLES.md)
