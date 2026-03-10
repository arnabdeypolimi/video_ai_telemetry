# Configuration Reference

## Configuration Methods

Three ways to configure ModalTrace, in order of precedence:

1. Python: `ModalTraceConfig(service_name="my-app")`
2. Environment variables: `MODALTRACE_SERVICE_NAME=my-app`
3. Defaults

---

## Service Identity

### `service_name`
- **Env:** `MODALTRACE_SERVICE_NAME` | **Default:** `modaltrace-pipeline`

### `service_version`
- **Env:** `MODALTRACE_SERVICE_VERSION` | **Default:** `0.0.0`

### `deployment_environment`
- **Env:** `MODALTRACE_DEPLOYMENT_ENVIRONMENT` | **Default:** `development`
- **Values:** `development`, `staging`, `production`

---

## OTLP Export

### `otlp_endpoint`
- **Env:** `MODALTRACE_OTLP_ENDPOINT` | **Default:** `http://localhost:4318`

### `otlp_protocol`
- **Env:** `MODALTRACE_OTLP_PROTOCOL` | **Default:** `http`
- **Values:** `http`, `grpc`

### `otlp_headers`
- **Env:** not supported | **Default:** `{}`
- ```python
  config = ModalTraceConfig(otlp_headers={"api-key": "your-key"})
  ```

### `otlp_timeout_ms`
- **Env:** `MODALTRACE_OTLP_TIMEOUT_MS` | **Default:** `10000`

---

## Feature Flags

### `pytorch_instrumentation`
- **Env:** `MODALTRACE_PYTORCH_INSTRUMENTATION` | **Default:** `true`

### `gpu_monitoring`
- **Env:** `MODALTRACE_GPU_MONITORING` | **Default:** `true`

### `webrtc_monitoring`
- **Env:** `MODALTRACE_WEBRTC_MONITORING` | **Default:** `false`

### `eventloop_monitoring`
- **Env:** `MODALTRACE_EVENTLOOP_MONITORING` | **Default:** `true`

### `threadpool_propagation`
- **Env:** `MODALTRACE_THREADPOOL_PROPAGATION` | **Default:** `true`

---

## Sampling

### `pytorch_sample_rate`
- **Env:** `MODALTRACE_PYTORCH_SAMPLE_RATE` | **Default:** `0.01` (1%)
- **Range:** `0.0`–`1.0`

### `anomaly_threshold_ms`
- **Env:** `MODALTRACE_ANOMALY_THRESHOLD_MS` | **Default:** `50.0`

### `span_window_s`
- **Env:** `MODALTRACE_SPAN_WINDOW_S` | **Default:** `1.0`

---

## Metrics

### `metrics_flush_interval_ms`
- **Env:** `MODALTRACE_METRICS_FLUSH_INTERVAL_MS` | **Default:** `1000`

### `ring_buffer_size`
- **Env:** `MODALTRACE_RING_BUFFER_SIZE` | **Default:** `512`
- Must be a power of 2: 256, 512, 1024, 2048, …

---

## Audio/Video Synchronization

### `av_drift_warning_ms`
- **Env:** `MODALTRACE_AV_DRIFT_WARNING_MS` | **Default:** `40.0`

### `av_chunk_ttl_s`
- **Env:** `MODALTRACE_AV_CHUNK_TTL_S` | **Default:** `5.0`

### `av_jitter_window`
- **Env:** `MODALTRACE_AV_JITTER_WINDOW` | **Default:** `30`

---

## GPU Monitoring

### `gpu_poll_interval_s`
- **Env:** `MODALTRACE_GPU_POLL_INTERVAL_S` | **Default:** `1.0`

### `gpu_device_indices`
- **Env:** not supported | **Default:** `None` (all devices)
- ```python
  config = ModalTraceConfig(gpu_device_indices=[0, 1])
  ```

---

## PyTorch Instrumentation

### `pytorch_track_memory`
- **Env:** `MODALTRACE_PYTORCH_TRACK_MEMORY` | **Default:** `true`

### `pytorch_track_shapes`
- **Env:** `MODALTRACE_PYTORCH_TRACK_SHAPES` | **Default:** `false`
- Captures tensor shapes; increases overhead.

---

## PII Scrubbing

### `scrubbing_enabled`
- **Env:** `MODALTRACE_SCRUBBING_ENABLED` | **Default:** `true`

### `scrubbing_patterns`
- **Env:** not supported | **Default:** `[]`
- ```python
  config = ModalTraceConfig(
      scrubbing_patterns=[
          r'\b\d{3}-\d{2}-\d{4}\b',  # SSN
          r'\b\d{16}\b',              # Credit card
      ]
  )
  ```

### `scrubbing_callback`
- **Env:** not supported | **Default:** `None`
- ```python
  def my_scrubber(value):
      if isinstance(value, str) and len(value) > 50:
          return value[:10] + "***REDACTED***"
      return value

  config = ModalTraceConfig(scrubbing_callback=my_scrubber)
  ```

---

## Logging

### `log_level`
- **Env:** `MODALTRACE_LOG_LEVEL` | **Default:** `info`
- **Values:** `debug`, `info`, `warning`, `error`, `critical`

### `log_console`
- **Env:** `MODALTRACE_LOG_CONSOLE` | **Default:** `true`

---

## Event Loop Monitoring

### `eventloop_lag_threshold_ms`
- **Env:** `MODALTRACE_EVENTLOOP_LAG_THRESHOLD_MS` | **Default:** `100.0`

---

## Dashboard

### `dashboard_port`
- **Env:** `MODALTRACE_DASHBOARD_PORT` | **Default:** `8000`
- The OTLP receiver always listens on port 4318.

---

## Configuration Examples

### Production

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
    pytorch_sample_rate=0.1,
    scrubbing_enabled=True,
    scrubbing_patterns=[r'\b\d{3}-\d{2}-\d{4}\b'],
)

sdk = ModalTraceSDK(config)
sdk.start()
```

### Local Development with Dashboard

```python
from modaltrace import ModalTraceSDK, ModalTraceConfig
from modaltrace.dashboard import DashboardServer

dashboard = DashboardServer()
dashboard.start()  # http://localhost:8000

config = ModalTraceConfig(
    service_name="video-pipeline-dev",
    deployment_environment="development",
    otlp_endpoint="http://localhost:4318",
    pytorch_instrumentation=True,
    gpu_monitoring=True,
    pytorch_sample_rate=1.0,
    log_level="debug",
)

sdk = ModalTraceSDK(config)
sdk.start()
```

### Low-Resource

```python
config = ModalTraceConfig(
    otlp_endpoint="http://collector:4318",
    pytorch_instrumentation=False,
    gpu_monitoring=False,
    webrtc_monitoring=False,
    ring_buffer_size=256,
    metrics_flush_interval_ms=2000,
    pytorch_sample_rate=0.001,
)
```
