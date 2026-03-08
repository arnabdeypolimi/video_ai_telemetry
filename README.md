# ModalTrace

<div align="center">

<img src="https://raw.githubusercontent.com/arnabdeypolimi/video_ai_telemetry/main/docs/logo.svg" alt="ModalTrace" width="320" />

<br/>

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![PyPI version](https://img.shields.io/pypi/v/modaltrace.svg)](https://pypi.org/project/modaltrace/)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-blue)](https://www.python.org/downloads/)
[![CI Status](https://github.com/arnabdeypolimi/video_ai_telemetry/actions/workflows/ci.yml/badge.svg)](https://github.com/arnabdeypolimi/video_ai_telemetry/actions)

**OpenTelemetry observability for real-time AI video applications**

[Docs](./docs/) • [API Reference](./docs/API.md) • [Examples](./docs/EXAMPLES.md) • [Comparison](./docs/COMPARISON.md) • [Issues](https://github.com/arnabdeypolimi/video_ai_telemetry/issues) • [Contributing](./CONTRIBUTING.md)

</div>

---

## 🚀 What is ModalTrace?

ModalTrace is an open-source OpenTelemetry library that provides production-grade observability for real-time AI video applications. It captures traces, metrics, and logs across your entire ML pipeline—from GPU operations and neural network inference to video rendering and transport layer performance.

Built for **production AI systems**, ModalTrace helps you understand latency bottlenecks, monitor resource utilization, and debug performance issues in complex distributed video AI pipelines.

<div align="center">

![ModalTrace Dashboard](https://raw.githubusercontent.com/arnabdeypolimi/video_ai_telemetry/main/docs/dashboard-demo.gif)

</div>

---

## Why ModalTrace?

Existing observability tools focus on LLM apps, batch ML training, or general APM — none target **real-time video AI pipelines**. ModalTrace is the only open-source library that provides frame-level metrics, A/V sync tracking, and pipeline stage tracing designed specifically for production video inference workloads.

| Feature | ModalTrace | Langfuse | Datadog | W&B |
|---------|:---------:|:--------:|:-------:|:---:|
| Video AI metrics | ✅ | ❌ | ❌ | ❌ |
| GPU monitoring | ✅ | ❌ | ✅ | ✅ |
| Frame-level metrics | ✅ | ❌ | ❌ | ❌ |
| A/V sync tracking | ✅ | ❌ | ❌ | ❌ |
| Pricing | Free OSS | $29+/mo | $31+/host/mo | Paid |

See the [full comparison →](./docs/COMPARISON.md)

---

## ✨ Features

**📊 Comprehensive Observability**
Trace execution paths across your entire pipeline with automatic span generation for each processing stage. Correlate traces with structured logging and metrics for complete visibility.

**⚡ Real-time Metrics**
Monitor frame rates, GPU memory allocation, inference latency, and synchronization drift with sub-millisecond precision. Built-in ring buffer aggregation for efficient metric collection.

**🔍 Semantic Conventions**
All telemetry uses standardized attribute keys (`modaltrace.*`) eliminating magic strings and enabling consistent instrumentation across teams.

**🧠 PyTorch & GPU Instrumentation**
Automatic instrumentation of PyTorch operations, GPU memory tracking, and device utilization metrics. Understand exactly where your model is spending time.

**🎬 Audio/Video Synchronization Tracking**
Detect and monitor A/V sync drift with configurable thresholds. Automatically log chunk mismatches and jitter metrics.

**🎯 Adaptive Sampling**
Intelligent span sampling based on anomaly detection. Automatically capture high-latency frames and unusual execution patterns without overwhelming your backend.

**🛡️ PII Scrubbing**
Built-in scrubbing pipeline removes sensitive data from logs and attributes. Customizable patterns for your specific compliance needs.

**📡 OpenTelemetry Export**
Native support for OTLP over HTTP and gRPC. Export to any OpenTelemetry-compatible backend: Jaeger, Datadog, New Relic, Honeycomb, or on-prem observability stacks.

---

## 🚀 Quick Start

### 1. Install

```bash
pip install modaltrace
```

For optional features (PyTorch, GPU, WebRTC, Dashboard):

```bash
pip install modaltrace[pytorch,gpu,webrtc,dashboard]
```

To install all features:

```bash
pip install modaltrace[all]
```

### 2. Configure & Initialize

Create a `.env` file or set environment variables:

```bash
MODALTRACE_SERVICE_NAME=my-video-pipeline
MODALTRACE_OTLP_ENDPOINT=http://localhost:4318
MODALTRACE_PYTORCH_INSTRUMENTATION=true
MODALTRACE_GPU_MONITORING=true
```

Initialize the SDK in your application:

```python
from modaltrace import ModalTraceSDK

sdk = ModalTraceSDK()
sdk.start()

# Your ML pipeline code here
# Spans are automatically created for instrumented operations
```

### 3. View Telemetry

#### Option A: Use ModalTrace Built-in Dashboard (Local Development)

Launch the built-in dashboard server:

```python
from modaltrace.dashboard import DashboardServer

server = DashboardServer()
server.start()  # http://localhost:8000
```

The dashboard provides:
- **Real-time stats**: FPS, latency P95, GPU metrics, A/V drift
- **Pipeline visualization**: Multi-stage latency chart
- **GPU monitoring**: Device-specific utilization, memory, temperature, power
- **Trace explorer**: 50 most recent spans with expandable attributes
- **Log viewer**: 100 most recent logs with severity filtering

#### Option B: Use External Observability Backend

Access your traces at your observability backend (e.g., `http://localhost:16686` for Jaeger, Datadog, Honeycomb):

```python
# Start a pipeline span
from modaltrace import get_tracer
tracer = get_tracer(__name__)

with tracer.start_as_current_span("process_frame") as span:
    span.set_attribute("modaltrace.pipeline.frame.sequence_number", frame_id)
    # Your frame processing logic here
```

---

## ⚙️ Configuration

All configuration is available via environment variables (prefix: `MODALTRACE_`) or Python kwargs to `ModalTraceConfig`:

| Setting | Env Variable | Type | Default | Description |
|---------|-------------|------|---------|-------------|
| **Service Identity** |
| `service_name` | `MODALTRACE_SERVICE_NAME` | str | `modaltrace-pipeline` | Service identifier in telemetry |
| `service_version` | `MODALTRACE_SERVICE_VERSION` | str | `0.0.0` | Semantic version of your service |
| `deployment_environment` | `MODALTRACE_DEPLOYMENT_ENVIRONMENT` | str | `development` | Environment (dev/staging/prod) |
| **OTLP Export** |
| `otlp_endpoint` | `MODALTRACE_OTLP_ENDPOINT` | URL | `http://localhost:4318` | OpenTelemetry collector endpoint |
| `otlp_protocol` | `MODALTRACE_OTLP_PROTOCOL` | str | `http` | Protocol: `http` or `grpc` |
| `otlp_timeout_ms` | `MODALTRACE_OTLP_TIMEOUT_MS` | int | `10000` | Export timeout in milliseconds |
| **Feature Flags** |
| `pytorch_instrumentation` | `MODALTRACE_PYTORCH_INSTRUMENTATION` | bool | `true` | Auto-instrument PyTorch ops |
| `gpu_monitoring` | `MODALTRACE_GPU_MONITORING` | bool | `true` | Track GPU metrics |
| `webrtc_monitoring` | `MODALTRACE_WEBRTC_MONITORING` | bool | `false` | Monitor WebRTC transports |
| `eventloop_monitoring` | `MODALTRACE_EVENTLOOP_MONITORING` | bool | `true` | Track event loop blocks |
| **Sampler** |
| `pytorch_sample_rate` | `MODALTRACE_PYTORCH_SAMPLE_RATE` | float (0-1) | `0.01` | Fraction of PyTorch ops to sample |
| `anomaly_threshold_ms` | `MODALTRACE_ANOMALY_THRESHOLD_MS` | float | `50.0` | Latency threshold for anomaly capture |
| **Metrics** |
| `metrics_flush_interval_ms` | `MODALTRACE_METRICS_FLUSH_INTERVAL_MS` | int | `1000` | Metric aggregation window |
| `ring_buffer_size` | `MODALTRACE_RING_BUFFER_SIZE` | int | `512` | Must be power of 2 |
| **A/V Sync** |
| `av_drift_warning_ms` | `MODALTRACE_AV_DRIFT_WARNING_MS` | float | `40.0` | Warn if drift exceeds this |
| `av_chunk_ttl_s` | `MODALTRACE_AV_CHUNK_TTL_S` | float | `5.0` | Chunk retention period |
| **PII Scrubbing** |
| `scrubbing_enabled` | `MODALTRACE_SCRUBBING_ENABLED` | bool | `true` | Enable PII removal |
| `scrubbing_patterns` | `MODALTRACE_SCRUBBING_PATTERNS` | list[str] | `[]` | Regex patterns to scrub |

---

## 📁 Architecture

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

## 🔧 Development

### Setup

```bash
git clone https://github.com/arnabdeypolimi/video_ai_telemetry.git
cd video_ai_telemetry
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e ".[dev,all]"
```

### Run Tests

```bash
pytest tests/ -v
```

### Lint & Format

```bash
ruff check src/ tests/
ruff format src/ tests/
```

### Type Check

```bash
mypy src/
```

---

## 🤝 Contributing

Contributions are welcome! Please:

1. Open an [issue](https://github.com/arnabdeypolimi/video_ai_telemetry/issues) to discuss changes
2. Fork the repository and create a feature branch
3. Submit a pull request with tests for new functionality
4. Ensure all tests pass and code is linted

For detailed guidelines, see [CONTRIBUTING.md](./CONTRIBUTING.md).

---

## 📄 License

ModalTrace is licensed under the Apache License 2.0. See [LICENSE](./LICENSE) for details.

---

**Questions?** Check the [documentation](./docs/), review [API reference](./docs/API.md), or open an [issue](https://github.com/arnabdeypolimi/video_ai_telemetry/issues).
