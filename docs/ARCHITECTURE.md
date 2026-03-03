# ModalTrace Architecture

## Overview

ModalTrace is an OpenTelemetry-based observability library designed for real-time AI video applications. It provides comprehensive tracing, metrics, and logging capabilities with minimal performance overhead.

## System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Application Code                      │
│  (PyTorch models, video rendering, pipeline stages)     │
└────────────────────┬────────────────────────────────────┘
                     │
        ┌────────────┼────────────┐
        │            │            │
        ▼            ▼            ▼
   ┌────────┐  ┌─────────┐  ┌──────────┐
   │Tracing │  │ Metrics │  │ Logging  │
   └────────┘  └─────────┘  └──────────┘
        │            │            │
        └────────────┼────────────┘
                     ▼
          ┌──────────────────────┐
          │  Span Processors     │
          │  - PII Scrubber      │
          │  - Pending Spans     │
          └──────────┬───────────┘
                     │
        ┌────────────┼────────────┐
        │            │            │
        ▼            ▼            ▼
   ┌────────┐  ┌──────────┐  ┌──────────┐
   │  OTLP  │  │ Logging  │  │ Metrics  │
   │ Export │  │ Handler  │  │Exporter  │
   └────┬───┘  └──────┬───┘  └────┬─────┘
        │             │            │
        └─────────────┼────────────┘
                      ▼
          ┌──────────────────────┐
          │ OpenTelemetry        │
          │ Collector/Backend    │
          │ (Jaeger, Datadog,    │
          │  etc.)               │
          └──────────────────────┘
```

## Dashboard (Optional Component)

The ModalTrace project includes an optional real-time dashboard for local development and monitoring. This is a FastAPI-based web application that receives OTLP telemetry data and visualizes it in real-time.

### Dashboard Architecture

```
┌──────────────────────────────┐
│    OTLP Telemetry Data       │
│  (Traces, Metrics, Logs)     │
└──────────────────────────────┘
                │
                ▼
┌──────────────────────────────┐
│   FastAPI Server             │
│  (/v1/traces, /v1/metrics,   │
│   /v1/logs, /api/*)          │
└──────────────────────────────┘
                │
    ┌───────────┼───────────┐
    ▼           ▼           ▼
 Spans       Metrics      Logs
  Store       Store       Store
    │           │           │
    └───────────┼───────────┘
                │
                ▼
┌──────────────────────────────┐
│   API Endpoints              │
│  - /api/spans                │
│  - /api/metrics/{name}       │
│  - /api/gpu                  │
│  - /api/logs                 │
└──────────────────────────────┘
                │
                ▼
┌──────────────────────────────┐
│   Single-Page HTML/JS App    │
│   (src/dashboard/static/)    │
│  - Stats Panel               │
│  - Pipeline Chart            │
│  - GPU Metrics               │
│  - Trace Table               │
│  - Log Viewer                │
└──────────────────────────────┘
```

### Dashboard Components

**Files:**
- `src/modaltrace/dashboard/server.py` - FastAPI OTLP receiver and API endpoints
- `src/modaltrace/dashboard/store.py` - Ring buffer storage for telemetry data
- `src/modaltrace/dashboard/proto_parser.py` - OTLP protobuf parsing
- `src/modaltrace/dashboard/static/index.html` - Frontend UI
- `src/modaltrace/dashboard/__main__.py` - CLI launcher

**Features:**
- Real-time telemetry visualization (updates every 2 seconds)
- Multi-stage pipeline latency chart with per-stage metrics
- GPU metrics dashboard (utilization, memory, temperature, power)
- Trace explorer with expandable attributes
- Structured log viewer with severity filtering
- Responsive dark theme UI (dark AI aesthetic)

**Data Flow:**
1. Application sends OTLP data to dashboard endpoint (port 4318 by default)
2. Dashboard receives and parses protobuf messages
3. Data stored in ring buffers (max 2000 spans, 10000 metrics, 5000 logs)
4. Frontend polls API endpoints every 2 seconds
5. Charts and tables updated with latest telemetry

## Core Components

### 1. Configuration (`config.py`)

**Purpose:** Single source of truth for all settings

**Key Features:**
- Pydantic-based settings model
- Environment variable support (`MODALTRACE_*`)
- Type-safe configuration validation
- .env file support

**Example:**
```python
from modaltrace import ModalTraceConfig

config = ModalTraceConfig(
    service_name="my-pipeline",
    pytorch_instrumentation=True,
    gpu_monitoring=True
)
```

### 2. Tracing (`tracing/`)

**Components:**

#### `pipeline.py`
- Main tracing orchestration
- Span creation and management
- Context management
- Pipeline stage decorators

#### `sampler.py`
- Adaptive sampling logic
- Anomaly detection
- Configurable sample rates
- Window-based sampling

#### `pending.py`
- Pending span processor
- Exports in-flight spans
- Useful for long-running pipelines
- Periodic flush mechanism

#### `propagation.py`
- ThreadPool context propagation
- ProcessPool context propagation
- Trace context preservation

### 3. Metrics (`metrics/`)

**Components:**

#### `instruments.py`
- Pre-allocated OTel instruments
- Histogram, counter, gauge definitions
- Lazy initialization

#### `aggregator.py`
- Ring buffer implementation
- High-performance hot path (~200ns)
- Daemon flush thread
- Batch metric export

#### `av_sync.py`
- Audio/Video synchronization tracking
- Drift measurement
- Jitter calculation
- Chunk correlation

### 4. Instrumentation (`instrumentation/`)

**Components:**

#### `pytorch.py`
- Auto-instrument torch.nn.Module
- Capture forward pass metrics
- Track memory allocation
- Two-tier recording (always + on-anomaly)

#### `gpu.py`
- NVML-based GPU monitoring
- Device utilization
- Memory metrics
- Temperature tracking
- Power consumption

#### `eventloop.py`
- Async event loop monitoring
- Block detection
- Latency tracking

#### `transport.py`
- WebRTC stats adapter
- RTT measurement
- Packet loss tracking
- Bitrate metrics

### 5. Logging (`logging/`)

**Components:**

#### `api.py`
- Structured logging API
- Trace context correlation
- Multiple log levels
- Context-aware logging

#### `scrubber.py`
- PII redaction
- Pattern-based scrubbing
- Custom callback support
- Secure by default

### 6. Conventions (`conventions/`)

**Components:**

#### `attributes.py`
- Semantic convention constants
- Zero magic strings in code
- Standardized attribute keys
- Consistent naming across components

**Attribute Categories:**
- `PipelineAttributes` - Pipeline-level metrics
- `InferenceAttributes` - Model inference data
- `ModalAttributes` - Avatar-specific metrics
- `AVSyncAttributes` - Audio/Video sync data
- `GPUAttributes` - GPU monitoring
- `TransportAttributes` - Network metrics
- `EventLoopAttributes` - Event loop metrics

### 7. Exporters (`exporters/`)

**Components:**

#### `setup.py`
- OTLP exporter initialization
- HTTP and gRPC transport support
- Batch span processor
- Header configuration

## Data Flow

### Tracing Flow

```
1. Application code starts span
   └─> Span created with context

2. Instrumentation captures metrics
   └─> Attributes added to span

3. PII Scrubber processes span
   └─> Sensitive data redacted

4. Pending Span Processor checks
   └─> Long-running spans exported

5. Batch Span Processor collects
   └─> Spans batched for efficiency

6. OTLP Exporter sends spans
   └─> HTTP/gRPC to backend
```

### Metrics Flow

```
1. Application records metric
   └─> Value added to ring buffer

2. Ring buffer aggregates
   └─> Efficient in-memory collection

3. Flush interval triggered
   └─> Daemon thread flushes metrics

4. Metric values aggregated
   └─> Sums, counts, percentiles

5. OTLP Metric Exporter sends
   └─> Batch export to backend
```

### Logging Flow

```
1. Application calls modaltrace.info()
   └─> Structured log created

2. Trace context injected
   └─> Correlation with spans

3. PII Scrubber processes
   └─> Sensitive fields redacted

4. Logging handler processes
   └─> Format and output

5. Sent to observability backend
   └─> Indexed with trace ID
```

## Performance Considerations

### Hot Path Optimization

- **Ring buffer metrics:** ~200ns overhead
- **Span recording:** Minimal allocation
- **Context propagation:** Efficient thread-local storage
- **Lazy initialization:** Deferred component startup

### Memory Management

- **Ring buffer:** Fixed-size circular buffer
- **Span batching:** Configurable batch sizes
- **Metric aggregation:** Window-based collection
- **Garbage collection:** Minimal pause times

### Thread Safety

- **Thread-safe instruments:** OTel SDK guarantees
- **Ring buffer:** Atomic operations
- **Context propagation:** Thread-local context vars
- **Async support:** asyncio-compatible

## Extension Points

### Custom Instrumentation

```python
from modaltrace import get_tracer

tracer = get_tracer(__name__)

with tracer.start_as_current_span("custom_operation") as span:
    span.set_attribute("custom.key", "value")
    # Your code here
```

### Custom Metrics

```python
from modaltrace.metrics import get_meter

meter = get_meter(__name__)
histogram = meter.create_histogram("custom.metric")
histogram.record(value=42)
```

### Custom Processors

Implement a `SpanProcessor` interface:

```python
from opentelemetry.sdk.trace import SpanProcessor

class CustomProcessor(SpanProcessor):
    def on_start(self, span: Span, parent_context) -> None:
        # Custom logic on span start
        pass

    def on_end(self, span: Span) -> None:
        # Custom logic on span end
        pass
```

## Deployment Architecture

### Single Machine

```
App + ModalTrace → OTLP Exporter → Jaeger/Datadog/etc
```

### Microservices

```
Service 1 ┐
Service 2 ├─→ OTLP Collector → Backend
Service 3 ┘
```

### Kubernetes

```
Pod (with sidecar) → Agent → Collector → Backend
```

## Future Enhancements

- [ ] Custom span exporters
- [ ] Distributed tracing improvements
- [ ] Performance profiling integration
- [ ] Cloud-native deployment templates
- [ ] Advanced sampling strategies
- [ ] Custom metric aggregation

---

For more details, see the [API documentation](./API.md) and [usage examples](./EXAMPLES.md).
