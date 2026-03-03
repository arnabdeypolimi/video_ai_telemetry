# ModalTrace Documentation

Welcome to **ModalTrace** - an open-source OpenTelemetry observability library for real-time AI video applications.

## Quick Navigation

- **[Getting Started](Getting-Started)** - Installation and first steps
- **[API Reference](API-Reference)** - Complete API documentation
- **[Architecture](Architecture)** - System design and components
- **[Examples](Examples)** - Practical usage examples
- **[Contributing](Contributing)** - How to contribute
- **[FAQ](FAQ)** - Frequently asked questions

## What is ModalTrace?

ModalTrace provides production-grade observability for real-time AI video pipelines. It captures:

- **Traces** - Execution paths across your entire pipeline
- **Metrics** - Real-time performance measurements
- **Logs** - Structured logging with trace correlation

## Key Features

✨ **Comprehensive Observability**
Trace execution paths with automatic span generation for each processing stage.

⚡ **Real-time Metrics**
Monitor frame rates, GPU memory, inference latency with sub-millisecond precision.

🔍 **Semantic Conventions**
Standardized attribute keys eliminate magic strings and ensure consistency.

🧠 **PyTorch & GPU Instrumentation**
Automatic instrumentation of PyTorch operations and GPU monitoring.

🎬 **A/V Synchronization Tracking**
Detect and monitor audio/video sync drift with configurable thresholds.

🎯 **Adaptive Sampling**
Intelligent span sampling based on anomaly detection.

🛡️ **PII Scrubbing**
Built-in scrubbing pipeline removes sensitive data from logs and attributes.

📡 **OpenTelemetry Export**
Native support for OTLP over HTTP and gRPC.

📊 **Built-in Dashboard**
Real-time telemetry visualization for local development (optional).

## Installation

```bash
pip install modaltrace
```

For optional features:

```bash
# Install with dashboard for local development
pip install modaltrace[dashboard]

# Or install all features
pip install modaltrace[all]
```

## Quick Start

```python
from modaltrace import ModalTraceSDK

# Initialize SDK
sdk = ModalTraceSDK()
sdk.start()

# Your ML pipeline code here
# Spans are automatically created for instrumented operations
```

## Documentation

- 📚 **[Full Documentation](.)** - Complete API and guides
- 🔧 **[Configuration](Configuration)** - All configuration options
- 📊 **[Examples](Examples)** - Real-world usage examples
- 🏗️ **[Architecture](Architecture)** - System design
- 🤝 **[Contributing](Contributing)** - Contribution guidelines

## Project Links

- **[GitHub Repository](https://github.com/arnabdeypolimi/video_ai_telemetry)**
- **[PyPI Package](https://pypi.org/project/modaltrace/)**
- **[GitHub Issues](https://github.com/arnabdeypolimi/video_ai_telemetry/issues)**
- **[License](https://github.com/arnabdeypolimi/video_ai_telemetry/blob/main/LICENSE)**

## Latest Release

**Version 0.2.0** - [Release Notes](https://github.com/arnabdeypolimi/video_ai_telemetry/releases/tag/v0.2.0)

- ✅ Comprehensive documentation
- ✅ API reference and examples
- ✅ Automated CI/CD pipeline
- ✅ PyPI publishing workflow

## Support

- **Questions?** Open an [issue](https://github.com/arnabdeypolimi/video_ai_telemetry/issues)
- **Want to contribute?** See [Contributing Guide](Contributing)
- **Need help?** Check [FAQ](FAQ)

---

**Last Updated:** March 1, 2026
