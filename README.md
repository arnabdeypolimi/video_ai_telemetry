# ModalTrace

<div align="center">

<img src="https://raw.githubusercontent.com/arnabdeypolimi/video_ai_telemetry/main/docs/logo.svg" alt="ModalTrace" width="320" />

<br/>

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![PyPI version](https://img.shields.io/pypi/v/modaltrace.svg)](https://pypi.org/project/modaltrace/)
[![PyPI downloads](https://img.shields.io/pypi/dm/modaltrace)](https://pypi.org/project/modaltrace/)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-blue)](https://www.python.org/downloads/)
[![CI Status](https://github.com/arnabdeypolimi/video_ai_telemetry/actions/workflows/ci.yml/badge.svg)](https://github.com/arnabdeypolimi/video_ai_telemetry/actions)

**OpenTelemetry observability for real-time AI video applications**

[Docs](./docs/) • [API Reference](./docs/API.md) • [Examples](./docs/EXAMPLES.md) • [Comparison](./docs/COMPARISON.md) • [Issues](https://github.com/arnabdeypolimi/video_ai_telemetry/issues) • [Contributing](./CONTRIBUTING.md)

</div>

---

ModalTrace is an OpenTelemetry library for real-time AI video pipelines. It captures traces, metrics, and logs across GPU operations, neural network inference, video rendering, and transport — with frame-level granularity and A/V sync tracking not available in general-purpose APM tools.

<div align="center">

![ModalTrace Dashboard](https://raw.githubusercontent.com/arnabdeypolimi/video_ai_telemetry/main/docs/dashboard-demo.gif)

</div>

---

## Why ModalTrace?

| Feature | ModalTrace | Langfuse | Datadog | W&B |
|---------|:---------:|:--------:|:-------:|:---:|
| Video AI metrics | ✅ | ❌ | ❌ | ❌ |
| GPU monitoring | ✅ | ❌ | ✅ | ✅ |
| Frame-level metrics | ✅ | ❌ | ❌ | ❌ |
| A/V sync tracking | ✅ | ❌ | ❌ | ❌ |
| Pricing | Free OSS | $29+/mo | $31+/host/mo | Paid |

See the [full comparison →](./docs/COMPARISON.md)

---

## Features

- Automatic span generation per pipeline stage with trace/metrics/log correlation
- Sub-millisecond frame rate, GPU memory, inference latency, and A/V drift metrics via ring buffer aggregation
- Standardized `modaltrace.*` attribute keys across all telemetry
- Auto-instrumentation for PyTorch forward/backward passes and GPU (utilization, memory, temperature, power)
- Adaptive sampling: anomaly-triggered capture for high-latency frames
- PII scrubbing with regex patterns and custom callbacks
- OTLP export over HTTP or gRPC to any compatible backend

---

## Quick Start

### Install

```bash
pip install modaltrace
```

Optional extras:

```bash
pip install modaltrace[pytorch,gpu,webrtc,dashboard]
# or
pip install modaltrace[all]
```

### Initialize

```python
from modaltrace import ModalTraceSDK

sdk = ModalTraceSDK()
sdk.start()

# your pipeline code here

sdk.shutdown()
```

Configuration via environment variables or `ModalTraceConfig`:

```bash
MODALTRACE_SERVICE_NAME=my-video-pipeline
MODALTRACE_OTLP_ENDPOINT=http://localhost:4318
MODALTRACE_PYTORCH_INSTRUMENTATION=true
MODALTRACE_GPU_MONITORING=true
```

### View telemetry

**Built-in dashboard** (local development):

```python
from modaltrace.dashboard import DashboardServer

server = DashboardServer()
server.start()  # http://localhost:8000
```

**External backend** (Jaeger, Datadog, Honeycomb, etc.):

```python
from modaltrace import get_tracer

tracer = get_tracer(__name__)

with tracer.start_as_current_span("process_frame") as span:
    span.set_attribute("modaltrace.pipeline.frame.sequence_number", frame_id)
    # your code here
```

---

## Configuration

All settings accept environment variables (`MODALTRACE_` prefix) or Python kwargs to `ModalTraceConfig`.

| Setting | Env Variable | Default | Description |
|---------|-------------|---------|-------------|
| **Service Identity** |
| `service_name` | `MODALTRACE_SERVICE_NAME` | `modaltrace-pipeline` | Service identifier in telemetry |
| `service_version` | `MODALTRACE_SERVICE_VERSION` | `0.0.0` | Semantic version |
| `deployment_environment` | `MODALTRACE_DEPLOYMENT_ENVIRONMENT` | `development` | Environment (dev/staging/prod) |
| **OTLP Export** |
| `otlp_endpoint` | `MODALTRACE_OTLP_ENDPOINT` | `http://localhost:4318` | Collector endpoint |
| `otlp_protocol` | `MODALTRACE_OTLP_PROTOCOL` | `http` | `http` or `grpc` |
| `otlp_timeout_ms` | `MODALTRACE_OTLP_TIMEOUT_MS` | `10000` | Export timeout (ms) |
| **Feature Flags** |
| `pytorch_instrumentation` | `MODALTRACE_PYTORCH_INSTRUMENTATION` | `true` | Auto-instrument PyTorch ops |
| `gpu_monitoring` | `MODALTRACE_GPU_MONITORING` | `true` | Track GPU metrics |
| `webrtc_monitoring` | `MODALTRACE_WEBRTC_MONITORING` | `false` | Monitor WebRTC transports |
| `eventloop_monitoring` | `MODALTRACE_EVENTLOOP_MONITORING` | `true` | Track event loop blocks |
| **Sampler** |
| `pytorch_sample_rate` | `MODALTRACE_PYTORCH_SAMPLE_RATE` | `0.01` | Fraction of PyTorch ops sampled |
| `anomaly_threshold_ms` | `MODALTRACE_ANOMALY_THRESHOLD_MS` | `50.0` | Latency threshold for anomaly capture |
| **Metrics** |
| `metrics_flush_interval_ms` | `MODALTRACE_METRICS_FLUSH_INTERVAL_MS` | `1000` | Aggregation window (ms) |
| `ring_buffer_size` | `MODALTRACE_RING_BUFFER_SIZE` | `512` | Must be power of 2 |
| **A/V Sync** |
| `av_drift_warning_ms` | `MODALTRACE_AV_DRIFT_WARNING_MS` | `40.0` | Warn if drift exceeds this (ms) |
| `av_chunk_ttl_s` | `MODALTRACE_AV_CHUNK_TTL_S` | `5.0` | Chunk retention period (s) |
| **PII Scrubbing** |
| `scrubbing_enabled` | `MODALTRACE_SCRUBBING_ENABLED` | `true` | Enable PII removal |
| `scrubbing_patterns` | `MODALTRACE_SCRUBBING_PATTERNS` | `[]` | Regex patterns to scrub |

---

## Architecture

```
modaltrace/
├── config.py                 # Pydantic configuration model
├── _registry.py             # Global SDK registry
├── conventions/
│   └── attributes.py        # Semantic convention constants
├── tracing/
│   ├── pipeline.py          # Main trace pipeline
│   ├── sampler.py           # Adaptive sampling logic
│   ├── pending.py           # Pending spans management
│   └── propagation.py       # Context propagation
├── metrics/
│   ├── instruments.py       # Metric instrument definitions
│   ├── aggregator.py        # Ring buffer aggregation
│   └── av_sync.py           # A/V sync metrics
├── instrumentation/
│   ├── pytorch.py           # PyTorch auto-instrumentation
│   ├── gpu.py               # GPU monitoring
│   ├── eventloop.py         # Event loop tracking
│   └── transport.py         # Network transport metrics
├── logging/
│   ├── api.py               # Structured logging API
│   └── scrubber.py          # PII scrubbing pipeline
└── exporters/
    └── setup.py             # OTLP exporter initialization
```

---

## Contributing

Open an [issue](https://github.com/arnabdeypolimi/video_ai_telemetry/issues) to discuss changes, then submit a PR with tests. See [CONTRIBUTING.md](./CONTRIBUTING.md) for setup and workflow details.

## License

Apache License 2.0. See [LICENSE](./LICENSE).
