# ModalTrace Documentation

ModalTrace is an OpenTelemetry observability library for real-time AI video pipelines.

## Navigation

- [Getting Started](Getting-Started) — installation and first steps
- [Configuration](Configuration) — all configuration options
- [API Reference](API-Reference) — complete API documentation
- [Examples](Examples) — usage examples
- [Architecture](Architecture) — system design
- [FAQ](FAQ) — troubleshooting and common questions
- [Contributing](Contributing) — contribution guidelines
- [Comparison](https://github.com/arnabdeypolimi/video_ai_telemetry/blob/main/docs/COMPARISON.md) — ModalTrace vs Langfuse, Datadog, W&B

## What ModalTrace captures

- **Traces** — execution paths across your pipeline, one span per stage
- **Metrics** — frame rate, inference latency, GPU utilization, A/V drift
- **Logs** — structured log records correlated to active trace spans

## Install

```bash
pip install modaltrace
# or
pip install modaltrace[all]
```

## Links

- [GitHub](https://github.com/arnabdeypolimi/video_ai_telemetry)
- [PyPI](https://pypi.org/project/modaltrace/)
- [Issues](https://github.com/arnabdeypolimi/video_ai_telemetry/issues)
- [License](https://github.com/arnabdeypolimi/video_ai_telemetry/blob/main/LICENSE)
