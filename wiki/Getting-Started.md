# Getting Started with ModalTrace

## Installation

```bash
pip install modaltrace
```

Optional extras:

```bash
pip install modaltrace[pytorch]    # PyTorch instrumentation
pip install modaltrace[gpu]        # GPU monitoring
pip install modaltrace[webrtc]     # WebRTC monitoring
pip install modaltrace[dashboard]  # Built-in dashboard
pip install modaltrace[all]        # Everything
```

## Quick Start

### 1. Initialize

```python
from modaltrace import ModalTraceSDK

sdk = ModalTraceSDK()
sdk.start()

try:
    pass  # your application code
finally:
    sdk.shutdown()
```

### 2. Configure

```python
from modaltrace import ModalTraceSDK, ModalTraceConfig

config = ModalTraceConfig(
    service_name="my-pipeline",
    deployment_environment="production",
    otlp_endpoint="http://localhost:4318",
    pytorch_instrumentation=True,
    gpu_monitoring=True,
)

sdk = ModalTraceSDK(config)
sdk.start()
```

Or via environment variables:

```bash
export MODALTRACE_SERVICE_NAME=my-pipeline
export MODALTRACE_OTLP_ENDPOINT=http://localhost:4318
export MODALTRACE_PYTORCH_INSTRUMENTATION=true
export MODALTRACE_GPU_MONITORING=true
```

### 3. Create Spans

```python
from modaltrace import get_tracer

tracer = get_tracer(__name__)

with tracer.start_as_current_span("process_frame") as span:
    span.set_attribute("frame_id", 42)
    result = process(frame)
```

### 4. Record Metrics

```python
from modaltrace import get_meter

meter = get_meter(__name__)
latency_histogram = meter.create_histogram("pipeline.latency", unit="ms")
latency_histogram.record(12.5)
```

### 5. Structured Logging

```python
from modaltrace.logging import info, error, warning

info("Processing started", pipeline="video-ai", frame_count=100)
error("Processing failed", error_code=500)
warning("High latency detected", latency_ms=150)
```

---

## Viewing Telemetry

### Option 1: Built-in Dashboard (local development)

```python
from modaltrace import ModalTraceSDK, ModalTraceConfig
from modaltrace.dashboard import DashboardServer

dashboard = DashboardServer()
dashboard.start()  # http://localhost:8000

config = ModalTraceConfig(
    service_name="my-pipeline",
    otlp_endpoint="http://localhost:4318",
)
sdk = ModalTraceSDK(config)
sdk.start()
```

The dashboard shows: FPS, latency percentiles, GPU metrics, A/V drift, pipeline latency chart, trace explorer, and log viewer.

### Option 2: Jaeger (local development)

```bash
docker run -d \
  --name jaeger \
  -p 4318:4318 \
  -p 16686:16686 \
  jaegertracing/all-in-one:latest
```

```python
sdk = ModalTraceSDK()  # uses localhost:4318 by default
sdk.start()
```

Access traces at `http://localhost:16686`.

### Option 3: Docker Compose

```yaml
version: '3'
services:
  jaeger:
    image: jaegertracing/all-in-one:latest
    ports:
      - "4318:4318"
      - "16686:16686"

  app:
    build: .
    environment:
      MODALTRACE_OTLP_ENDPOINT: http://jaeger:4318
    depends_on:
      - jaeger
```

### Option 4: Cloud Services

**Datadog:**
```python
config = ModalTraceConfig(
    otlp_endpoint="https://opentelemetry.datadoghq.com/v1/traces",
    otlp_protocol="http",
)
```

**New Relic:**
```python
config = ModalTraceConfig(
    otlp_endpoint="https://otlp.nr-data.net:4318",
    otlp_headers={"api-key": "YOUR_API_KEY"},
)
```

---

## Next Steps

- [Configuration Reference](Configuration) — all configuration options
- [API Reference](API-Reference) — full API
- [Examples](Examples) — real-world patterns
- [Architecture](Architecture) — system design

---

## Troubleshooting

**Spans not appearing**

1. Verify the OTLP endpoint is reachable: `curl http://localhost:4318/v1/traces`
2. Confirm `service_name` is set
3. Check that your backend is running

**Import errors**

```bash
pip install modaltrace[all]
```

**High memory usage**

```python
config = ModalTraceConfig(
    ring_buffer_size=256,          # default: 512
    metrics_flush_interval_ms=2000 # default: 1000
)
```

**GPU monitoring shows no data**

1. Check `nvidia-smi` to confirm the GPU is visible
2. Install `pynvml`: `pip install pynvml`
3. Set `MODALTRACE_GPU_MONITORING=true`

See [FAQ](FAQ) for more.
