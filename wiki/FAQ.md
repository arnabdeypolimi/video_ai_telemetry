# Frequently Asked Questions

## General

**What is ModalTrace?**
An OpenTelemetry library for real-time AI video pipelines. It captures traces, metrics, and logs with frame-level granularity, A/V sync tracking, and GPU monitoring not found in general-purpose APM tools.

**How does ModalTrace compare to Langfuse, Datadog, or W&B?**
Those tools target LLM apps, enterprise APM, or batch training respectively. ModalTrace is purpose-built for real-time video AI: frame-level metrics, A/V sync drift, and pipeline stage tracing. Since it exports standard OTLP, it can work alongside any of them. See the [full comparison](https://github.com/arnabdeypolimi/video_ai_telemetry/blob/main/docs/COMPARISON.md).

**What Python versions are supported?**
Python 3.10, 3.11, and 3.12.

---

## Installation & Setup

**How do I install ModalTrace?**
```bash
pip install modaltrace
# with optional features:
pip install modaltrace[pytorch,gpu,webrtc]
```

**Do I need an observability backend?**
No, but you won't see telemetry without one. Use the built-in dashboard (`pip install modaltrace[dashboard]`) for local development, or Jaeger for a lightweight local backend.

---

## Configuration

**How do I configure ModalTrace?**
Three ways, in order of precedence:
1. Python: `ModalTraceConfig(service_name="my-app")`
2. Environment variables: `MODALTRACE_SERVICE_NAME=my-app`
3. Defaults

**What is the default OTLP endpoint?**
`http://localhost:4318`

**How do I export to Datadog?**
```python
config = ModalTraceConfig(
    otlp_endpoint="https://opentelemetry.datadoghq.com/v1/traces",
    otlp_headers={"api-key": "YOUR_API_KEY"},
)
```

**Can I use multiple backends simultaneously?**
Not directly, but you can route through an OpenTelemetry Collector configured to fan out to multiple backends.

---

## Performance

**What is the performance overhead?**
Typically < 5% for ring buffer metrics. Varies based on configuration and workload.

**How much memory does ModalTrace use?**
~50MB with defaults. Reduce with a smaller ring buffer:

```python
config = ModalTraceConfig(
    ring_buffer_size=256,          # default: 512
    metrics_flush_interval_ms=2000 # default: 1000
)
```

---

## Features

**Does ModalTrace support my framework?**
Auto-instrumentation is provided for PyTorch and GPU (NVIDIA). For other frameworks, use the manual tracing API.

**Does ModalTrace support asyncio?**
Yes, with automatic context propagation via `contextvars`. For thread/process pools, use `propagate_context`:

```python
from modaltrace.tracing.propagation import propagate_context
from concurrent.futures import ThreadPoolExecutor

with ThreadPoolExecutor() as executor:
    executor.submit(propagate_context(my_function))
```

---

## Security & Privacy

**Can ModalTrace redact sensitive data?**
Yes. PII scrubbing is enabled by default. Add custom regex patterns or a callback:

```python
config = ModalTraceConfig(
    scrubbing_patterns=[r'\b\d{3}-\d{2}-\d{4}\b']  # SSN
)
```

**What data does ModalTrace collect?**
Only what you explicitly record in spans, metrics, and logs. No telemetry is sent to Anthropic or any third party — data goes to your configured OTLP backend.

**Can I disable individual features?**
```python
config = ModalTraceConfig(
    pytorch_instrumentation=False,
    gpu_monitoring=False,
    webrtc_monitoring=False,
)
```

---

## Troubleshooting

**Spans aren't appearing in my backend**
1. Verify the endpoint: `curl http://localhost:4318/v1/traces`
2. Check `service_name` is set
3. Confirm the backend is running
4. Check logs for export errors

**GPU monitoring shows no data**
1. Confirm `nvidia-smi` works
2. Install `pynvml`: `pip install pynvml`
3. Set `MODALTRACE_GPU_MONITORING=true`

---

[Open an issue](https://github.com/arnabdeypolimi/video_ai_telemetry/issues) if your question isn't answered here.
