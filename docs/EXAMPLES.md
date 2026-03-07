# ModalTrace Usage Examples

<img src="logo.svg" alt="ModalTrace" width="240" />

## Basic Usage

### Initialize ModalTrace

```python
from modaltrace import ModalTraceSDK, get_tracer

# Initialize SDK
sdk = ModalTraceSDK()
sdk.start()

# Get a tracer
tracer = get_tracer(__name__)

try:
    # Your application code here
    with tracer.start_as_current_span("main_operation") as span:
        span.set_attribute("operation.type", "inference")
        result = run_inference()
finally:
    sdk.shutdown()
```

### Configuration

```python
from modaltrace import ModalTraceSDK, ModalTraceConfig

# Configure with custom settings
config = ModalTraceConfig(
    service_name="video-ai-pipeline",
    service_version="1.0.0",
    deployment_environment="production",
    otlp_endpoint="http://localhost:4318",
    pytorch_instrumentation=True,
    gpu_monitoring=True,
)

sdk = ModalTraceSDK(config)
sdk.start()
```

### Configuration via Environment Variables

```bash
# .env file
MODALTRACE_SERVICE_NAME=my-pipeline
MODALTRACE_OTLP_ENDPOINT=http://collector:4318
MODALTRACE_PYTORCH_INSTRUMENTATION=true
MODALTRACE_GPU_MONITORING=true
```

```python
from modaltrace import ModalTraceSDK

# Configuration loaded from environment
sdk = ModalTraceSDK()
sdk.start()
```

## Pipeline Tracing

### Trace Pipeline Stages

```python
from modaltrace import get_tracer
from modaltrace.conventions.attributes import PipelineAttributes

tracer = get_tracer(__name__)

def process_video_frame(frame_id, frame_data):
    """Process a single video frame."""
    with tracer.start_as_current_span("process_frame") as span:
        span.set_attribute(PipelineAttributes.FRAME_SEQ, frame_id)
        span.set_attribute(PipelineAttributes.TARGET_FPS, 30)

        # Stage 1: Preprocessing
        with tracer.start_as_current_span("preprocessing") as preproc_span:
            preprocessed = preprocess(frame_data)
            preproc_span.set_attribute("preprocessing.duration_ms", 5.2)

        # Stage 2: Inference
        with tracer.start_as_current_span("inference") as infer_span:
            result = model(preprocessed)
            infer_span.set_attribute("inference.duration_ms", 12.1)

        # Stage 3: Postprocessing
        with tracer.start_as_current_span("postprocessing") as post_span:
            final_result = postprocess(result)
            post_span.set_attribute("postprocessing.duration_ms", 3.4)

        return final_result
```

## PyTorch Integration

### Auto-Instrumented PyTorch

PyTorch operations are automatically instrumented with ModalTrace enabled:

```python
import torch
import torch.nn as nn
from modaltrace import ModalTraceSDK, get_tracer

sdk = ModalTraceSDK()
sdk.start()

tracer = get_tracer(__name__)

class MyModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.linear = nn.Linear(10, 5)

    def forward(self, x):
        return self.linear(x)

model = MyModel()

with tracer.start_as_current_span("training_step") as span:
    x = torch.randn(32, 10)
    output = model(x)  # Automatically traced!
    loss = output.sum()
    loss.backward()  # Backward pass also traced

    span.set_attribute("batch_size", 32)
    span.set_attribute("learning_rate", 0.001)
```

### Manual PyTorch Metrics

```python
from modaltrace import get_meter
from modaltrace.conventions.attributes import InferenceAttributes

meter = get_meter(__name__)
forward_latency = meter.create_histogram("model.forward_latency", unit="ms")

def train_step(model, data, targets):
    start = time.time()
    outputs = model(data)
    latency = (time.time() - start) * 1000
    forward_latency.record(latency)

    loss = criterion(outputs, targets)
    loss.backward()
    return loss.item()
```

## GPU Monitoring

### Track GPU Usage

```python
from modaltrace import ModalTraceSDK, get_tracer
from modaltrace.conventions.attributes import GPUAttributes

sdk = ModalTraceSDK()
sdk.start()

tracer = get_tracer(__name__)

def gpu_intensive_operation():
    """GPU monitoring is automatic with gpu_monitoring=True."""
    with tracer.start_as_current_span("gpu_operation") as span:
        # GPU metrics are automatically recorded
        # - modaltrace.gpu.device_index
        # - modaltrace.gpu.utilization
        # - modaltrace.gpu.memory.used
        # - modaltrace.gpu.memory.free
        # - modaltrace.gpu.temperature
        # - modaltrace.gpu.power.draw

        tensor = torch.randn(10000, 10000).cuda()
        result = torch.matmul(tensor, tensor)

        span.set_attribute("matrix_size", 10000)
```

## Metrics Collection

### Ring Buffer Metrics

```python
from modaltrace import ModalTraceSDK, get_meter

sdk = ModalTraceSDK()
sdk.start()

meter = get_meter(__name__)

# Create metric instruments
frame_latency = meter.create_histogram(
    "frame.latency",
    unit="ms",
    description="Frame processing latency"
)

frames_processed = meter.create_counter(
    "frames.processed",
    description="Number of frames processed"
)

queue_size = meter.create_gauge(
    "processing.queue_size",
    description="Current processing queue size"
)

# Record metrics (high-performance ring buffer)
for frame in frame_stream:
    start = time.time()

    process_frame(frame)
    latency = (time.time() - start) * 1000

    frame_latency.record(latency)
    frames_processed.add(1)
    queue_size.set(get_queue_size())
```

## Structured Logging

### Log with Context

```python
from modaltrace.logging import info, error, warning, debug
from modaltrace import get_tracer

tracer = get_tracer(__name__)

def process_batch(batch_id, batch_data):
    with tracer.start_as_current_span("batch_processing") as span:
        info("Processing batch", batch_id=batch_id, size=len(batch_data))

        try:
            results = []
            for item_id, item in enumerate(batch_data):
                debug("Processing item", item_id=item_id, batch_id=batch_id)
                result = process_item(item)
                results.append(result)

            info(
                "Batch completed",
                batch_id=batch_id,
                items_processed=len(results),
                duration_ms=span.duration
            )

        except Exception as e:
            error(
                "Batch processing failed",
                batch_id=batch_id,
                error=str(e),
                error_type=type(e).__name__
            )
            raise
```

## Audio/Video Synchronization

### Track A/V Sync Metrics

```python
from modaltrace import ModalTraceSDK, get_tracer
from modaltrace.conventions.attributes import AVSyncAttributes

sdk = ModalTraceSDK()
sdk.start()

tracer = get_tracer(__name__)

def process_av_stream():
    audio_chunks = {}
    video_frames = {}

    with tracer.start_as_current_span("av_pipeline") as span:
        # Capture audio chunk
        audio_chunk_id = 100
        audio_timestamp = time.time()
        audio_chunks[audio_chunk_id] = audio_timestamp

        # Later: Render video frame
        video_chunk_id = 100
        video_timestamp = time.time()

        # Calculate drift
        drift_ms = (video_timestamp - audio_chunks[video_chunk_id]) * 1000

        with tracer.start_as_current_span("av_sync") as sync_span:
            sync_span.set_attribute(AVSyncAttributes.CHUNK_ID, video_chunk_id)
            sync_span.set_attribute(AVSyncAttributes.DRIFT_MS, drift_ms)

            if abs(drift_ms) > 40:  # Threshold
                sync_span.set_attribute(AVSyncAttributes.THRESHOLD_MS, 40)
                warning("A/V sync drift detected", drift_ms=drift_ms)
```

## Error Handling and Exceptions

### Record Exceptions in Spans

```python
from opentelemetry.trace import Status, StatusCode
from modaltrace import get_tracer

tracer = get_tracer(__name__)

def risky_operation():
    try:
        with tracer.start_as_current_span("risky_op") as span:
            result = perform_operation()
            span.set_status(Status(StatusCode.OK))
            return result

    except ValueError as e:
        span.record_exception(e)
        span.set_status(Status(StatusCode.ERROR, description=str(e)))
        error("Operation failed", error=str(e), error_type="ValueError")
        raise

    except Exception as e:
        span.record_exception(e)
        span.set_status(Status(StatusCode.ERROR, description="Unknown error"))
        error("Unexpected error", error=str(e))
        raise
```

## PII Scrubbing

### Automatic PII Removal

```python
from modaltrace import ModalTraceSDK, ModalTraceConfig, get_tracer

# Configure PII scrubbing
config = ModalTraceConfig(
    scrubbing_enabled=True,
    scrubbing_patterns=[
        r'\b\d{3}-\d{2}-\d{4}\b',  # SSN
        r'\b\d{16}\b',              # Credit card
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Email
    ]
)

sdk = ModalTraceSDK(config)
sdk.start()

tracer = get_tracer(__name__)

# Spans with sensitive data are automatically scrubbed
with tracer.start_as_current_span("user_processing") as span:
    # These values will be scrubbed from telemetry
    span.set_attribute("ssn", "123-45-6789")
    span.set_attribute("credit_card", "1234567890123456")
    span.set_attribute("email", "user@example.com")
    span.set_attribute("user_id", "safe-value")
```

## Async Operations

### Trace Async Code

```python
import asyncio
from modaltrace import get_tracer

tracer = get_tracer(__name__)

async def async_operation():
    with tracer.start_as_current_span("async_op") as span:
        # Context is automatically propagated to async tasks
        result = await some_async_work()
        span.set_attribute("result", result)
        return result

async def main():
    with tracer.start_as_current_span("main") as span:
        tasks = [
            async_operation(),
            async_operation(),
            async_operation(),
        ]
        results = await asyncio.gather(*tasks)
        span.set_attribute("total_results", len(results))

asyncio.run(main())
```

## Custom Span Processors

### Add Custom Processing

```python
from opentelemetry.sdk.trace import SpanProcessor
from opentelemetry.trace import Span

class LoggingSpanProcessor(SpanProcessor):
    """Log all spans as they start and end."""

    def on_start(self, span: Span, parent_context) -> None:
        print(f"Span started: {span.name}")

    def on_end(self, span: Span) -> None:
        print(f"Span ended: {span.name} ({span.end_time - span.start_time}ns)")

    def shutdown(self) -> None:
        pass

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        return True

# Register processor
from opentelemetry import trace

sdk = ModalTraceSDK()
sdk.start()
trace.get_tracer_provider().add_span_processor(LoggingSpanProcessor())
```

## Full Example: Video Processing Pipeline

```python
import asyncio
from modaltrace import ModalTraceSDK, ModalTraceConfig, get_tracer, get_meter
from modaltrace.logging import info, error
from modaltrace.conventions.attributes import (
    PipelineAttributes,
    InferenceAttributes,
    GPUAttributes,
)

# Configure ModalTrace
config = ModalTraceConfig(
    service_name="video-processing-pipeline",
    deployment_environment="production",
    pytorch_instrumentation=True,
    gpu_monitoring=True,
)

sdk = ModalTraceSDK(config)
sdk.start()

tracer = get_tracer(__name__)
meter = get_meter(__name__)

# Create metrics
frame_latency = meter.create_histogram("pipeline.frame.latency", unit="ms")
frames_processed = meter.create_counter("pipeline.frames.processed")

async def process_video_stream(video_file):
    """Process a video file frame by frame."""
    with tracer.start_as_current_span("video_processing") as span:
        span.set_attribute("video_file", video_file)
        info("Starting video processing", video_file=video_file)

        frame_count = 0
        try:
            for frame_id, frame in enumerate(load_frames(video_file)):
                with tracer.start_as_current_span("process_frame") as frame_span:
                    import time
                    start = time.time()

                    frame_span.set_attribute(PipelineAttributes.FRAME_SEQ, frame_id)

                    # Preprocess
                    with tracer.start_as_current_span("preprocess"):
                        frame = preprocess(frame)

                    # Inference
                    with tracer.start_as_current_span("inference") as infer_span:
                        result = model(frame)
                        infer_span.set_attribute(InferenceAttributes.FORWARD_PASS_MS, 12.5)

                    # Postprocess
                    with tracer.start_as_current_span("postprocess"):
                        output = postprocess(result)

                    latency = (time.time() - start) * 1000
                    frame_latency.record(latency)
                    frames_processed.add(1)
                    frame_count += 1

            info("Video processing completed", frames_processed=frame_count)

        except Exception as e:
            error("Video processing failed", error=str(e), frames_processed=frame_count)
            raise

# Run the pipeline
if __name__ == "__main__":
    try:
        asyncio.run(process_video_stream("video.mp4"))
    finally:
        sdk.shutdown()
```

## Dashboard Integration

### Launch the Built-in Dashboard

For local development, use the built-in dashboard to visualize telemetry in real-time:

```python
from modaltrace import ModalTraceSDK, ModalTraceConfig, get_tracer
from modaltrace.dashboard import DashboardServer

# Start the dashboard server
# - Dashboard UI: http://localhost:8000
# - OTLP receiver: http://localhost:4318
dashboard = DashboardServer()
dashboard.start()

# Configure SDK to send to dashboard
config = ModalTraceConfig(
    service_name="my-pipeline",
    otlp_endpoint="http://localhost:4318",
    pytorch_instrumentation=True,
    gpu_monitoring=True,
)

sdk = ModalTraceSDK(config)
sdk.start()

tracer = get_tracer(__name__)

# Your telemetry is now visible at http://localhost:8000
with tracer.start_as_current_span("main") as span:
    span.set_attribute("modaltrace.pipeline.frame.sequence_number", 0)
    # Your code here
```

### Dashboard Features

The dashboard provides real-time visualization of:

- **Stats Panel**: FPS, Inference/Render/Encode P95 latencies, dropped frames, A/V drift
- **Pipeline Chart**: Multi-stage latency trends over 60 seconds
- **GPU Metrics**: Device utilization, memory usage, temperature, power consumption
- **Trace Explorer**: Browse 50 recent spans with expandable attributes
- **Log Viewer**: Search 100 recent logs with severity filtering

### Configure Dashboard Telemetry

For the dashboard to display all metrics properly, ensure your telemetry includes:

```python
from modaltrace import get_tracer, get_meter
from modaltrace.conventions.attributes import PipelineAttributes

tracer = get_tracer(__name__)
meter = get_meter(__name__)

# Create metrics the dashboard expects
pipeline_latency = meter.create_histogram(
    "modaltrace.pipeline.stage.duration",
    unit="ms",
    description="Pipeline stage latency"
)

dropped_frames = meter.create_counter(
    "modaltrace.frames.dropped",
    description="Frames dropped"
)

av_drift = meter.create_gauge(
    "modaltrace.av_sync.drift",
    unit="ms",
    description="Audio/Video sync drift"
)

def process_frame(frame_id, frame_data):
    with tracer.start_as_current_span("process_frame") as span:
        span.set_attribute(PipelineAttributes.FRAME_SEQ, frame_id)

        # Inference stage
        import time
        start = time.time()
        result = model(frame_data)
        latency = (time.time() - start) * 1000

        # Record stage latency with stage attribute
        pipeline_latency.record(
            latency,
            attributes={"modaltrace.pipeline.stage": "inference"}
        )

        # Record other metrics
        dropped_frames.add(0)  # or 1 if frame was dropped
        av_drift.set(2.5)  # milliseconds

        return result
```

---

For more detailed API reference, see [API.md](./API.md)
