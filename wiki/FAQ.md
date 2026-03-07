# Frequently Asked Questions

## General Questions

### Q: What is ModalTrace?
A: ModalTrace is an open-source OpenTelemetry library that provides observability for real-time AI video applications. It captures traces, metrics, and logs with minimal performance overhead.

### Q: What are the system requirements?
A: Python 3.10 or later. Optional dependencies include PyTorch, pynvml for GPU monitoring, and aiortc for WebRTC support.

### Q: Is ModalTrace free?
A: Yes! ModalTrace is licensed under Apache-2.0, a permissive open-source license.

### Q: How does ModalTrace compare to Langfuse, Datadog, or W&B?
A: ModalTrace is the only observability library purpose-built for real-time video AI pipelines. Tools like Langfuse focus on LLM apps, Datadog on enterprise APM, and W&B on batch training — none offer native frame-level metrics, A/V sync tracking, or video pipeline stage tracing. Since ModalTrace exports standard OTLP, it works alongside any of these tools. See the [full comparison](https://github.com/arnabdeypolimi/video_ai_telemetry/blob/main/docs/COMPARISON.md) for details.

## Installation & Setup

### Q: How do I install ModalTrace?
A: Install from PyPI:
```bash
pip install modaltrace
```

Or with optional features:
```bash
pip install modaltrace[pytorch,gpu,webrtc]
```

### Q: Which Python versions are supported?
A: Python 3.10, 3.11, and 3.12.

### Q: I'm getting an import error. What's wrong?
A: Make sure all dependencies are installed:
```bash
pip install modaltrace[all]
```

### Q: Do I need an observability backend to use ModalTrace?
A: No, but without one you won't see the telemetry. We recommend Jaeger for local development.

## Configuration

### Q: How do I configure ModalTrace?
A: Three ways (in order of precedence):
1. Python code: `ModalTraceConfig(service_name="my-app")`
2. Environment variables: `MODALTRACE_SERVICE_NAME=my-app`
3. Default values

### Q: What's the default OTLP endpoint?
A: `http://localhost:4318` (assumes local Jaeger or OpenTelemetry Collector)

### Q: How do I export to Datadog?
A: Set the OTLP endpoint and headers:
```python
config = ModalTraceConfig(
    otlp_endpoint="https://opentelemetry.datadoghq.com/v1/traces",
    otlp_headers={"api-key": "YOUR_API_KEY"},
)
```

### Q: Can I use multiple backends?
A: No, but you can use an OpenTelemetry Collector to forward to multiple backends.

## Performance

### Q: What's the performance overhead?
A: Typically < 5% for ring buffer metrics. Varies based on configuration and workload.

### Q: How much memory does ModalTrace use?
A: Default ~50MB. Can be reduced with smaller ring buffer size.

### Q: Can I reduce memory usage?
A: Yes:
```python
config = ModalTraceConfig(
    ring_buffer_size=256,  # Default is 512
    metrics_flush_interval_ms=2000,  # Default is 1000
)
```

### Q: What if spans aren't being captured?
A: Check:
1. Instrumentation is enabled in config
2. OTLP endpoint is reachable
3. Service name is set
4. Backend is running

## Features

### Q: Does ModalTrace support my framework?
A: ModalTrace provides auto-instrumentation for PyTorch and GPU operations. For other frameworks, use the manual API.

### Q: Can I create custom spans?
A: Yes:
```python
from modaltrace import get_tracer
tracer = get_tracer(__name__)
with tracer.start_as_current_span("my_operation"):
    # Your code
```

### Q: What about custom metrics?
A: Yes:
```python
from modaltrace import get_meter
meter = get_meter(__name__)
histogram = meter.create_histogram("custom.metric")
histogram.record(value)
```

### Q: Does ModalTrace support asynchronous code?
A: Yes, full asyncio support with automatic context propagation.

## Security & Privacy

### Q: Is telemetry data secure?
A: ModalTrace exports to your own OTLP backend. Data transmission security depends on your backend configuration (use HTTPS/TLS).

### Q: Can ModalTrace redact sensitive data?
A: Yes, PII scrubbing is enabled by default with customizable patterns.

### Q: What data does ModalTrace collect?
A: Only what you explicitly record in spans, metrics, and logs. No automatic data collection beyond framework events.

### Q: Can I disable certain features?
A: Yes, use feature flags:
```python
config = ModalTraceConfig(
    pytorch_instrumentation=False,
    gpu_monitoring=False,
    webrtc_monitoring=False,
)
```

## Troubleshooting

### Q: Spans aren't appearing in my backend
A:
1. Verify OTLP endpoint is correct: `curl http://localhost:4318/v1/traces`
2. Check service_name is set
3. Ensure backend is running
4. Check logs for errors
5. Verify network connectivity

### Q: High memory usage
A: Reduce buffer size or increase flush intervals:
```python
config = ModalTraceConfig(
    ring_buffer_size=256,
    metrics_flush_interval_ms=2000,
)
```

### Q: PyTorch instrumentation not working
A: Ensure PyTorch is installed:
```bash
pip install torch
```

### Q: GPU monitoring shows no data
A:
1. Check if NVIDIA GPU is installed: `nvidia-smi`
2. Install pynvml: `pip install pynvml`
3. Enable GPU monitoring: `MODALTRACE_GPU_MONITORING=true`

### Q: Asyncio context not propagating
A: Use the context propagation API:
```python
from modaltrace.tracing.propagation import propagate_context
with ThreadPoolExecutor() as executor:
    executor.submit(propagate_context(my_function))
```

## Contributing

### Q: How can I contribute?
A: See the [Contributing Guide](Contributing) in the repository.

### Q: Where do I report bugs?
A: Open an [issue](https://github.com/arnabdeypolimi/video_ai_telemetry/issues) on GitHub.

### Q: Can I request features?
A: Yes, open a [feature request](https://github.com/arnabdeypolimi/video_ai_telemetry/issues) on GitHub.

## Getting Help

### Q: Where can I get help?
A:
1. Check this FAQ
2. Read the [documentation](https://github.com/arnabdeypolimi/video_ai_telemetry/wiki)
3. Open a [GitHub issue](https://github.com/arnabdeypolimi/video_ai_telemetry/issues)
4. Check the [Examples](Examples) page

### Q: Is there a Slack/Discord community?
A: Not yet, but you're welcome to open discussions on GitHub.

---

Can't find your answer? [Open an issue](https://github.com/arnabdeypolimi/video_ai_telemetry/issues) and we'll help!
