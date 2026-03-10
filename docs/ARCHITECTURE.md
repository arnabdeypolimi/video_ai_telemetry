# ModalTrace Architecture

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
          └──────────────────────┘
```

## Dashboard (Optional)

A FastAPI server that receives OTLP telemetry and serves a real-time web UI.

```
┌──────────────────────────────┐
│    OTLP Telemetry Data       │
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
└──────────────────────────────┘
```

**Files:**
- `src/modaltrace/dashboard/server.py` — FastAPI OTLP receiver and API endpoints
- `src/modaltrace/dashboard/store.py` — ring buffer storage (2000 spans, 10000 metrics, 5000 logs)
- `src/modaltrace/dashboard/proto_parser.py` — OTLP protobuf parsing
- `src/modaltrace/dashboard/static/index.html` — frontend UI
- `src/modaltrace/dashboard/__main__.py` — CLI launcher

**Data flow:**
1. Application sends OTLP to port 4318
2. Dashboard parses protobuf and stores in ring buffers
3. Frontend polls `/api/*` every 2 seconds

---

## Core Components

### `config.py`

Pydantic settings model. Reads from `MODALTRACE_*` environment variables, `.env` files, or constructor kwargs. Single source of truth for all SDK settings.

---

### `tracing/`

| File | Responsibility |
|------|---------------|
| `pipeline.py` | Span creation, context management, pipeline stage decorators |
| `sampler.py` | Window-based adaptive sampling with anomaly detection |
| `pending.py` | Exports in-flight spans periodically (for long-running pipelines) |
| `propagation.py` | Trace context propagation to thread/process pools |

---

### `metrics/`

| File | Responsibility |
|------|---------------|
| `instruments.py` | Pre-allocated OTel histogram, counter, gauge definitions |
| `aggregator.py` | Fixed-size ring buffer (~200ns hot path), daemon flush thread, batch export |
| `av_sync.py` | A/V drift measurement, jitter calculation, chunk correlation |

---

### `instrumentation/`

| File | Responsibility |
|------|---------------|
| `pytorch.py` | Monkey-patches `torch.nn.Module` forward; two-tier recording (always + on-anomaly) |
| `gpu.py` | NVML-based polling for utilization, memory, temperature, power |
| `eventloop.py` | Asyncio event loop lag detection |
| `transport.py` | WebRTC RTT, packet loss, bitrate metrics |

---

### `logging/`

| File | Responsibility |
|------|---------------|
| `api.py` | Structured logging with trace context correlation |
| `scrubber.py` | Pattern-based PII redaction with custom callback support |

---

### `conventions/attributes.py`

Semantic constant classes (`PipelineAttributes`, `InferenceAttributes`, `GPUAttributes`, `AVSyncAttributes`, `TransportAttributes`, `EventLoopAttributes`, `ModalAttributes`). Eliminates magic strings across the codebase.

---

### `exporters/setup.py`

Initializes OTLP batch span processor and metric exporter. Supports HTTP and gRPC transports with configurable headers and timeouts.

---

## Data Flow

### Tracing

1. Application starts a span
2. Instrumentation adds attributes
3. PII scrubber redacts sensitive fields
4. Pending span processor exports long-running spans
5. Batch span processor collects and sends via OTLP

### Metrics

1. Application records a value → ring buffer
2. Daemon flush thread fires on interval
3. Aggregated values (sums, counts, percentiles) exported via OTLP

### Logging

1. Application calls `modaltrace.info()` → structured log created
2. Active trace context injected (trace_id, span_id)
3. PII scrubber processes fields
4. Sent to backend indexed by trace ID

---

## Performance

- **Ring buffer metrics:** ~200ns per record
- **Span recording:** minimal allocation, thread-local context vars
- **Memory:** fixed-size buffers; configurable ring buffer size and batch sizes
- **Async:** full asyncio support with `contextvars`-based propagation

---

## Deployment

```
# Single machine
App + ModalTrace → OTLP Exporter → Jaeger/Datadog/etc

# Microservices
Service 1 ┐
Service 2 ├─→ OTLP Collector → Backend
Service 3 ┘

# Kubernetes
Pod (with sidecar) → Agent → Collector → Backend
```

---

For API details, see [API.md](./API.md). For usage examples, see [EXAMPLES.md](./EXAMPLES.md).
