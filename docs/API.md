# ModalTrace API Reference

## Core Classes

### ModalTraceConfig

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
- `service_name` (str, default: `"modaltrace-pipeline"`)
- `service_version` (str, default: `"0.0.0"`)
- `deployment_environment` (str, default: `"development"`)

**OTLP Export:**
- `otlp_endpoint` (URL, default: `"http://localhost:4318"`)
- `otlp_protocol` (str, default: `"http"`) — `"http"` or `"grpc"`
- `otlp_headers` (dict, default: `{}`)
- `otlp_timeout_ms` (int, default: `10000`)

**Feature Flags:**
- `pytorch_instrumentation` (bool, default: `True`)
- `gpu_monitoring` (bool, default: `True`)
- `webrtc_monitoring` (bool, default: `False`)
- `eventloop_monitoring` (bool, default: `True`)

**Sampling:**
- `pytorch_sample_rate` (float, default: `0.01`)
- `anomaly_threshold_ms` (float, default: `50.0`)
- `span_window_s` (float, default: `1.0`)

**Metrics:**
- `metrics_flush_interval_ms` (int, default: `1000`)
- `ring_buffer_size` (int, default: `512`) — must be power of 2

**Audio/Video Sync:**
- `av_drift_warning_ms` (float, default: `40.0`)
- `av_chunk_ttl_s` (float, default: `5.0`)
- `av_jitter_window` (int, default: `30`)

**GPU Monitoring:**
- `gpu_poll_interval_s` (float, default: `1.0`)
- `gpu_device_indices` (list[int], optional) — defaults to all devices

**PII Scrubbing:**
- `scrubbing_enabled` (bool, default: `True`)
- `scrubbing_patterns` (list[str], default: `[]`)
- `scrubbing_callback` (callable, optional)

**Logging:**
- `log_level` (str, default: `"info"`)
- `log_console` (bool, default: `True`)

---

### ModalTraceSDK

```python
from modaltrace import ModalTraceSDK

sdk = ModalTraceSDK()
sdk.start()

# ...

sdk.shutdown()
```

#### Methods

```python
def start() -> None: ...
def shutdown(timeout_ms: int = 30000) -> None: ...
def get_tracer(name: str) -> Tracer: ...
def get_meter(name: str) -> Meter: ...
def get_logger(name: str) -> Logger: ...
```

---

## Tracing API

```python
from modaltrace import get_tracer

tracer = get_tracer(__name__)

with tracer.start_as_current_span("operation_name") as span:
    span.set_attribute("key", "value")
```

### Span methods

```python
span.set_attribute(key: str, value: Any) -> None
span.add_event(name: str, attributes: dict = None, timestamp: int = None) -> None
span.record_exception(exception: Exception, attributes: dict = None) -> None
span.set_status(status: Status) -> None
```

### Error handling

```python
from opentelemetry.trace import Status, StatusCode

try:
    with tracer.start_as_current_span("risky_operation") as span:
        result = risky_function()
        span.set_status(Status(StatusCode.OK))
except Exception as e:
    span.record_exception(e)
    span.set_status(Status(StatusCode.ERROR, description=str(e)))
    raise
```

---

## Metrics API

```python
from modaltrace.metrics import get_meter

meter = get_meter(__name__)

histogram = meter.create_histogram("inference.latency", unit="ms")
histogram.record(12.5)

counter = meter.create_counter("frames.processed")
counter.add(1)

gauge = meter.create_gauge("gpu.memory", unit="MB")
gauge.set(4096)
```

---

## Logging API

```python
from modaltrace.logging import info, error, warning, debug

info("Processing frame", frame_id=42, fps=30)
error("Inference failed", error_code=500)
warning("GPU temperature high", temperature_c=85)
debug("Internal state", state={"queue_size": 10})
```

---

## Semantic Conventions

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

span.set_attribute(PipelineAttributes.FRAME_SEQ, 0)
span.set_attribute(PipelineAttributes.TARGET_FPS, 30)
span.set_attribute(InferenceAttributes.MODEL_NAME, "my-model")
span.set_attribute(InferenceAttributes.FORWARD_PASS_MS, 11.5)
span.set_attribute(GPUAttributes.DEVICE_INDEX, 0)
span.set_attribute(AVSyncAttributes.DRIFT_MS, 5.2)
```

---

## Advanced Usage

### Custom Span Processor

```python
from opentelemetry.sdk.trace import SpanProcessor
from opentelemetry.trace import Span

class CustomProcessor(SpanProcessor):
    def on_start(self, span: Span, parent_context) -> None: ...
    def on_end(self, span: Span) -> None: ...
    def shutdown(self) -> None: ...
    def force_flush(self, timeout_millis: int = 30000) -> bool: return True

from opentelemetry import trace
trace.get_tracer_provider().add_span_processor(CustomProcessor())
```

### PII Scrubbing

```python
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

config = ModalTraceConfig(scrubbing_callback=custom_scrubber)
```

### Context Propagation

```python
from modaltrace.tracing.propagation import propagate_context
from concurrent.futures import ThreadPoolExecutor

def worker(task_id):
    tracer = get_tracer(__name__)
    with tracer.start_as_current_span(f"task_{task_id}"):
        pass

with ThreadPoolExecutor() as executor:
    for i in range(10):
        executor.submit(propagate_context(worker), i)
```

---

## Dashboard API Endpoints

The dashboard server (`pip install modaltrace[dashboard]`) receives OTLP on port 4318 and serves the UI and query APIs on port 8000.

### OTLP Receiver

```
POST /v1/traces
POST /v1/metrics
POST /v1/logs
```

### Query Endpoints

**Spans**

```
GET /api/spans?since_ms=<timestamp>&limit=50
```

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
    "attributes": { "modaltrace.pipeline.frame.sequence_number": 42 }
  }
]
```

**Metrics**

```
GET /api/metrics/{name}?since_ms=<timestamp>
```

```json
[
  {
    "name": "modaltrace.pipeline.stage.duration",
    "value": 45.3,
    "timestamp_ms": 1234567890,
    "attributes": { "modaltrace.pipeline.stage": "inference" },
    "percentiles": { "p50": 40.0, "p95": 45.3, "p99": 50.0 }
  }
]
```

**GPU**

```
GET /api/gpu
```

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

**Logs**

```
GET /api/logs?since_ms=<timestamp>&level=<ERROR|WARN|INFO>&limit=100
```

```json
[
  {
    "timestamp_ms": 1234567890,
    "severity": "ERROR",
    "body": "GPU memory allocation failed",
    "trace_id": "abc123...",
    "span_id": "def456...",
    "attributes": { "error.code": 500 }
  }
]
```

### Dashboard Setup

```python
from modaltrace import ModalTraceConfig, ModalTraceSDK
from modaltrace.dashboard import DashboardServer

server = DashboardServer()
server.start()  # http://localhost:8000

config = ModalTraceConfig(
    service_name="my-pipeline",
    otlp_endpoint="http://localhost:4318",
)
sdk = ModalTraceSDK(config)
sdk.start()
```

---

For examples, see [EXAMPLES.md](./EXAMPLES.md).
