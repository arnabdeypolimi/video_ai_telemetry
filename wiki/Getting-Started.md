# Getting Started with ModalTrace

## Installation

### Basic Installation

```bash
pip install modaltrace
```

### With Optional Features

```bash
# PyTorch instrumentation
pip install modaltrace[pytorch]

# GPU monitoring
pip install modaltrace[gpu]

# WebRTC monitoring
pip install modaltrace[webrtc]

# All features
pip install modaltrace[all]
```

## Quick Start (5 minutes)

### 1. Initialize ModalTrace

```python
from modaltrace import ModalTraceSDK

# Create and start SDK
sdk = ModalTraceSDK()
sdk.start()

try:
    # Your application code here
    pass
finally:
    # Shutdown and flush telemetry
    sdk.shutdown()
```

### 2. Configure (Optional)

Set environment variables or pass configuration:

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

Or use environment variables:

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
    # Your code here
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

## Running with OpenTelemetry Backend

### Option 1: Local Jaeger (Recommended for Testing)

```bash
# Start Jaeger with Docker
docker run -d \
  --name jaeger \
  -p 4318:4318 \
  -p 16686:16686 \
  jaegertracing/all-in-one:latest
```

Then run your application:

```python
from modaltrace import ModalTraceSDK

sdk = ModalTraceSDK()  # Uses localhost:4318 by default
sdk.start()

# Your code here

sdk.shutdown()
```

Access traces at: `http://localhost:16686`

### Option 2: Docker Compose

```yaml
version: '3'
services:
  jaeger:
    image: jaegertracing/all-in-one:latest
    ports:
      - "4318:4318"  # OTLP HTTP
      - "16686:16686"  # UI

  app:
    build: .
    environment:
      MODALTRACE_OTLP_ENDPOINT: http://jaeger:4318
    depends_on:
      - jaeger
```

### Option 3: Cloud Services

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

## Next Steps

1. **[Configuration Guide](Configuration)** - Learn about all configuration options
2. **[API Reference](API-Reference)** - Explore the full API
3. **[Examples](Examples)** - See real-world usage patterns
4. **[Architecture](Architecture)** - Understand the system design

## Troubleshooting

### Spans not appearing

1. Check OTLP endpoint is reachable:
   ```python
   import urllib.request
   urllib.request.urlopen("http://localhost:4318/v1/traces")
   ```

2. Verify service name is set:
   ```python
   from modaltrace import ModalTraceConfig
   config = ModalTraceConfig(service_name="my-service")
   ```

3. Check logs for errors

### Import errors

Make sure all dependencies are installed:

```bash
pip install modaltrace[all]
```

### High memory usage

Reduce ring buffer size or increase flush interval:

```python
config = ModalTraceConfig(
    ring_buffer_size=256,  # Default is 512
    metrics_flush_interval_ms=2000,  # Default is 1000
)
```

## Common Issues

See [FAQ](FAQ) for more troubleshooting.
