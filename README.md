# avatar-otel

OpenTelemetry observability for real-time AI avatar and video pipelines.

## Features

- **One-liner init** — `avatar_otel.init(service_name="my-pipeline")` wires up traces, metrics, and logs
- **Pipeline stage tracing** — `@pipeline_stage` decorator and `stage()` context manager with adaptive sampling
- **Frame metrics aggregator** — Ring buffer with ~200ns hot-path overhead, daemon flush to OTel
- **A/V sync tracking** — Drift and jitter measurement with warning callbacks
- **PyTorch auto-instrumentation** — Two-tier recording (ring buffer always, span on 1% or slow)
- **GPU monitoring** — NVML-backed utilization, memory, temperature, power gauges
- **WebRTC transport metrics** — RTT, jitter, packet loss, frame rate from aiortc stats
- **Structured logging** — `avatar_otel.info("msg", key=value)` with trace context correlation
- **PII scrubbing** — Span processor redacting sensitive attribute patterns
- **Context propagation** — ThreadPool/ProcessPool OTel context forwarding
- **Event loop monitor** — Detects asyncio blocking above threshold
- **Pending span snapshots** — Exports in-flight spans for long-running pipeline visibility

## Quick start

```bash
pip install avatar-otel
# With optional extras:
pip install avatar-otel[pytorch,gpu,webrtc]
# Or everything:
pip install avatar-otel[all]
```

```python
import avatar_otel

# Initialize — configurable via kwargs or AVATAR_OTEL_* env vars
with avatar_otel.init(service_name="artalk-avatar") as sdk:

    # Trace pipeline stages
    @avatar_otel.pipeline_stage("flame_inference")
    async def run_flame_model(params):
        return model(params)

    # Context manager for ad-hoc stages
    with avatar_otel.stage("render") as s:
        s.record("vertex_count", 12345)
        frame = render(mesh)

    # Structured logging with trace correlation
    avatar_otel.info("Frame rendered", fps=30, resolution="1080p")

    # Frame metrics (hot path)
    sdk.frame_aggregator.record(forward_pass_ms=11.2, render_ms=3.1)

    # A/V sync tracking
    sdk.av_tracker.audio_captured(chunk_id=42)
    # ... later ...
    drift = sdk.av_tracker.frame_rendered(chunk_id=42)
```

## Configuration

All settings via `AvatarOtelConfig` (Pydantic Settings):

| Setting | Env var | Default |
|---------|---------|---------|
| `service_name` | `AVATAR_OTEL_SERVICE_NAME` | `avatar-pipeline` |
| `otlp_endpoint` | `AVATAR_OTEL_OTLP_ENDPOINT` | `http://localhost:4318` |
| `otlp_protocol` | `AVATAR_OTEL_OTLP_PROTOCOL` | `http` |
| `pytorch_instrumentation` | `AVATAR_OTEL_PYTORCH_INSTRUMENTATION` | `true` |
| `gpu_monitoring` | `AVATAR_OTEL_GPU_MONITORING` | `true` |
| `ring_buffer_size` | `AVATAR_OTEL_RING_BUFFER_SIZE` | `512` |
| `av_drift_warning_ms` | `AVATAR_OTEL_AV_DRIFT_WARNING_MS` | `40.0` |
| `pytorch_sample_rate` | `AVATAR_OTEL_PYTORCH_SAMPLE_RATE` | `0.01` |

See `avatar_otel.config.AvatarOtelConfig` for the full list.

## Architecture

```
avatar_otel/
├── __init__.py              # Public API + init() orchestration
├── config.py                # Pydantic Settings model
├── conventions/
│   └── attributes.py        # Semantic convention constants
├── tracing/
│   ├── sampler.py           # AdaptiveSampler (force/anomaly/window)
│   ├── pipeline.py          # @pipeline_stage, stage(), async_stage()
│   ├── pending.py           # PendingSpanProcessor
│   └── propagation.py       # ThreadPool/ProcessPool context propagation
├── metrics/
│   ├── instruments.py       # Pre-allocated OTel instruments
│   ├── aggregator.py        # Ring buffer + flush thread
│   └── av_sync.py           # AVSyncTracker
├── logging/
│   ├── api.py               # Structured log functions
│   └── scrubber.py          # PII redaction processor
├── instrumentation/
│   ├── pytorch.py           # torch.nn.Module.__call__ patch
│   ├── gpu.py               # NVML poller
│   ├── eventloop.py         # asyncio Handle._run patch
│   └── transport.py         # WebRTC stats adapter
└── exporters/
    └── setup.py             # OTLP provider configuration
```

## Development

```bash
# Clone and install
git clone https://github.com/arnabdeypolimi/video_ai_telemetry.git
cd video_ai_telemetry
uv venv && uv pip install -e ".[dev]" --python .venv/bin/python

# Run tests
.venv/bin/python -m pytest tests/ -v

# Lint
.venv/bin/ruff check src/ tests/
```

## License

Apache-2.0
