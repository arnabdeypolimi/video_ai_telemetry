# Configuration Reference

## Configuration Methods

ModalTrace can be configured in three ways (in order of precedence):

1. **Python Code** (highest priority)
   ```python
   config = ModalTraceConfig(service_name="my-app")
   ```

2. **Environment Variables** (medium priority)
   ```bash
   export MODALTRACE_SERVICE_NAME=my-app
   ```

3. **Default Values** (lowest priority)

## Service Identity

### service_name
- **Env Var:** `MODALTRACE_SERVICE_NAME`
- **Default:** `modaltrace-pipeline`
- **Description:** Service identifier in telemetry
- **Example:** `my-video-processor`

### service_version
- **Env Var:** `MODALTRACE_SERVICE_VERSION`
- **Default:** `0.0.0`
- **Description:** Semantic version of your service
- **Example:** `1.2.3`

### deployment_environment
- **Env Var:** `MODALTRACE_DEPLOYMENT_ENVIRONMENT`
- **Default:** `development`
- **Description:** Environment name
- **Values:** `development`, `staging`, `production`

## OTLP Export

### otlp_endpoint
- **Env Var:** `MODALTRACE_OTLP_ENDPOINT`
- **Default:** `http://localhost:4318`
- **Description:** OpenTelemetry collector endpoint
- **Example:** `http://jaeger:4318` or `https://otlp.nr-data.net:4318`

### otlp_protocol
- **Env Var:** `MODALTRACE_OTLP_PROTOCOL`
- **Default:** `http`
- **Description:** Transport protocol
- **Values:** `http`, `grpc`

### otlp_headers
- **Env Var:** (Not supported via env)
- **Default:** `{}`
- **Description:** Custom HTTP headers
- **Example:**
  ```python
  config = ModalTraceConfig(
      otlp_headers={"api-key": "your-key"}
  )
  ```

### otlp_timeout_ms
- **Env Var:** `MODALTRACE_OTLP_TIMEOUT_MS`
- **Default:** `10000`
- **Description:** Export timeout in milliseconds

## Feature Flags

### pytorch_instrumentation
- **Env Var:** `MODALTRACE_PYTORCH_INSTRUMENTATION`
- **Default:** `true`
- **Description:** Auto-instrument PyTorch operations
- **Values:** `true`, `false`

### gpu_monitoring
- **Env Var:** `MODALTRACE_GPU_MONITORING`
- **Default:** `true`
- **Description:** Enable GPU metrics collection
- **Values:** `true`, `false`

### webrtc_monitoring
- **Env Var:** `MODALTRACE_WEBRTC_MONITORING`
- **Default:** `false`
- **Description:** Monitor WebRTC connections
- **Values:** `true`, `false`

### eventloop_monitoring
- **Env Var:** `MODALTRACE_EVENTLOOP_MONITORING`
- **Default:** `true`
- **Description:** Track asyncio event loop blocks
- **Values:** `true`, `false`

### threadpool_propagation
- **Env Var:** `MODALTRACE_THREADPOOL_PROPAGATION`
- **Default:** `true`
- **Description:** Propagate context to thread/process pools
- **Values:** `true`, `false`

## Sampling Configuration

### pytorch_sample_rate
- **Env Var:** `MODALTRACE_PYTORCH_SAMPLE_RATE`
- **Default:** `0.01` (1%)
- **Description:** Fraction of PyTorch ops to sample
- **Range:** `0.0` to `1.0`

### anomaly_threshold_ms
- **Env Var:** `MODALTRACE_ANOMALY_THRESHOLD_MS`
- **Default:** `50.0`
- **Description:** Latency threshold for anomaly capture
- **Unit:** milliseconds

### span_window_s
- **Env Var:** `MODALTRACE_SPAN_WINDOW_S`
- **Default:** `1.0`
- **Description:** Sampling window duration
- **Unit:** seconds

## Metrics Configuration

### metrics_flush_interval_ms
- **Env Var:** `MODALTRACE_METRICS_FLUSH_INTERVAL_MS`
- **Default:** `1000`
- **Description:** Metric aggregation flush interval
- **Unit:** milliseconds

### ring_buffer_size
- **Env Var:** `MODALTRACE_RING_BUFFER_SIZE`
- **Default:** `512`
- **Description:** Ring buffer size for metrics (must be power of 2)
- **Valid Values:** 256, 512, 1024, 2048, etc.

## Audio/Video Synchronization

### av_drift_warning_ms
- **Env Var:** `MODALTRACE_AV_DRIFT_WARNING_MS`
- **Default:** `40.0`
- **Description:** A/V sync drift warning threshold
- **Unit:** milliseconds

### av_chunk_ttl_s
- **Env Var:** `MODALTRACE_AV_CHUNK_TTL_S`
- **Default:** `5.0`
- **Description:** Chunk retention period
- **Unit:** seconds

### av_jitter_window
- **Env Var:** `MODALTRACE_AV_JITTER_WINDOW`
- **Default:** `30`
- **Description:** Jitter measurement window size

## GPU Monitoring

### gpu_poll_interval_s
- **Env Var:** `MODALTRACE_GPU_POLL_INTERVAL_S`
- **Default:** `1.0`
- **Description:** GPU metrics polling interval
- **Unit:** seconds

### gpu_device_indices
- **Env Var:** (Not supported via env)
- **Default:** `None` (all devices)
- **Description:** Specific GPUs to monitor
- **Example:**
  ```python
  config = ModalTraceConfig(gpu_device_indices=[0, 1])
  ```

## PyTorch Instrumentation

### pytorch_track_memory
- **Env Var:** `MODALTRACE_PYTORCH_TRACK_MEMORY`
- **Default:** `true`
- **Description:** Track GPU memory allocation
- **Values:** `true`, `false`

### pytorch_track_shapes
- **Env Var:** `MODALTRACE_PYTORCH_TRACK_SHAPES`
- **Default:** `false`
- **Description:** Track tensor shapes (higher overhead)
- **Values:** `true`, `false`

## PII Scrubbing

### scrubbing_enabled
- **Env Var:** `MODALTRACE_SCRUBBING_ENABLED`
- **Default:** `true`
- **Description:** Enable PII redaction
- **Values:** `true`, `false`

### scrubbing_patterns
- **Env Var:** (Not supported via env)
- **Default:** `[]`
- **Description:** Regex patterns for PII detection
- **Example:**
  ```python
  config = ModalTraceConfig(
      scrubbing_patterns=[
          r'\b\d{3}-\d{2}-\d{4}\b',  # SSN
          r'\b\d{16}\b',              # Credit card
      ]
  )
  ```

### scrubbing_callback
- **Env Var:** (Not supported via env)
- **Default:** `None`
- **Description:** Custom scrubbing function
- **Example:**
  ```python
  def my_scrubber(value):
      if isinstance(value, str) and len(value) > 50:
          return value[:10] + "***REDACTED***"
      return value

  config = ModalTraceConfig(scrubbing_callback=my_scrubber)
  ```

## Logging Configuration

### log_level
- **Env Var:** `MODALTRACE_LOG_LEVEL`
- **Default:** `info`
- **Values:** `debug`, `info`, `warning`, `error`, `critical`

### log_console
- **Env Var:** `MODALTRACE_LOG_CONSOLE`
- **Default:** `true`
- **Description:** Output logs to console
- **Values:** `true`, `false`

## Event Loop Monitoring

### eventloop_lag_threshold_ms
- **Env Var:** `MODALTRACE_EVENTLOOP_LAG_THRESHOLD_MS`
- **Default:** `100.0`
- **Description:** Event loop lag threshold
- **Unit:** milliseconds

## Dashboard Configuration (Optional)

The built-in dashboard can be launched for local development and real-time telemetry visualization.

### dashboard_port
- **Env Var:** `MODALTRACE_DASHBOARD_PORT`
- **Default:** `8000`
- **Description:** Port for dashboard web UI
- **Note:** OTLP receiver listens on port 4318

### Dashboard with SDK

```python
from modaltrace import ModalTraceSDK, ModalTraceConfig
from modaltrace.dashboard import DashboardServer

# Start dashboard
dashboard = DashboardServer()
dashboard.start()

# Configure SDK to send to dashboard
config = ModalTraceConfig(
    service_name="my-pipeline",
    otlp_endpoint="http://localhost:4318",  # Send to dashboard
    pytorch_instrumentation=True,
    gpu_monitoring=True,
)

sdk = ModalTraceSDK(config)
sdk.start()

# View at http://localhost:8000
```

## Configuration Examples

### Production Setup

```python
from modaltrace import ModalTraceSDK, ModalTraceConfig

config = ModalTraceConfig(
    service_name="video-pipeline",
    service_version="1.0.0",
    deployment_environment="production",
    otlp_endpoint="https://otlp.nr-data.net:4318",
    otlp_headers={"api-key": "YOUR_API_KEY"},
    pytorch_instrumentation=True,
    gpu_monitoring=True,
    pytorch_sample_rate=0.1,  # 10% sampling
    scrubbing_enabled=True,
    scrubbing_patterns=[r'\b\d{3}-\d{2}-\d{4}\b'],
)

sdk = ModalTraceSDK(config)
sdk.start()
```

### Development Setup with Dashboard

```python
from modaltrace import ModalTraceSDK, ModalTraceConfig
from modaltrace.dashboard import DashboardServer

# Start dashboard server
dashboard = DashboardServer()
dashboard.start()  # http://localhost:8000

# Configure to send to dashboard
config = ModalTraceConfig(
    service_name="video-pipeline-dev",
    deployment_environment="development",
    otlp_endpoint="http://localhost:4318",  # Dashboard receiver
    pytorch_instrumentation=True,
    gpu_monitoring=True,
    pytorch_sample_rate=1.0,  # Sample everything
    log_level="debug",
)

sdk = ModalTraceSDK(config)
sdk.start()
```

### Development Setup with External Backend

```python
from modaltrace import ModalTraceSDK, ModalTraceConfig

config = ModalTraceConfig(
    service_name="video-pipeline-dev",
    deployment_environment="development",
    otlp_endpoint="http://localhost:4318",  # Local Jaeger
    pytorch_instrumentation=True,
    gpu_monitoring=True,
    pytorch_sample_rate=1.0,  # Sample everything
    log_level="debug",
)

sdk = ModalTraceSDK(config)
sdk.start()
```

### Low-Resource Setup

```python
from modaltrace import ModalTraceSDK, ModalTraceConfig

config = ModalTraceConfig(
    otlp_endpoint="http://collector:4318",
    pytorch_instrumentation=False,  # Disable if not needed
    gpu_monitoring=False,
    webrtc_monitoring=False,
    ring_buffer_size=256,  # Smaller buffer
    metrics_flush_interval_ms=2000,  # Less frequent flushes
    pytorch_sample_rate=0.001,  # Very low sampling
)

sdk = ModalTraceSDK(config)
sdk.start()
```
