# ModalTrace Usage Examples

## Basic Setup

```python
from modaltrace import ModalTraceSDK, ModalTraceConfig, get_tracer

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

tracer = get_tracer(__name__)

try:
    with tracer.start_as_current_span("main_operation") as span:
        span.set_attribute("operation.type", "inference")
        result = run_inference()
finally:
    sdk.shutdown()
```

Configuration via environment variables is also supported — see [Configuration](../wiki/Configuration.md).

---

## Pipeline Tracing

```python
from modaltrace import get_tracer
from modaltrace.conventions.attributes import PipelineAttributes

tracer = get_tracer(__name__)

def process_video_frame(frame_id, frame_data):
    with tracer.start_as_current_span("process_frame") as span:
        span.set_attribute(PipelineAttributes.FRAME_SEQ, frame_id)
        span.set_attribute(PipelineAttributes.TARGET_FPS, 30)

        with tracer.start_as_current_span("preprocessing") as preproc_span:
            preprocessed = preprocess(frame_data)
            preproc_span.set_attribute("preprocessing.duration_ms", 5.2)

        with tracer.start_as_current_span("inference") as infer_span:
            result = model(preprocessed)
            infer_span.set_attribute("inference.duration_ms", 12.1)

        with tracer.start_as_current_span("postprocessing") as post_span:
            final_result = postprocess(result)
            post_span.set_attribute("postprocessing.duration_ms", 3.4)

        return final_result
```

---

## PyTorch Integration

PyTorch operations are automatically instrumented when `pytorch_instrumentation=True`:

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
    output = model(x)  # automatically traced
    loss = output.sum()
    loss.backward()

    span.set_attribute("batch_size", 32)
    span.set_attribute("learning_rate", 0.001)
```

Manual histogram for custom latency tracking:

```python
from modaltrace import get_meter
import time

meter = get_meter(__name__)
forward_latency = meter.create_histogram("model.forward_latency", unit="ms")

def train_step(model, data, targets):
    start = time.time()
    outputs = model(data)
    forward_latency.record((time.time() - start) * 1000)

    loss = criterion(outputs, targets)
    loss.backward()
    return loss.item()
```

---

## GPU Monitoring

GPU metrics are recorded automatically when `gpu_monitoring=True`. The following attributes are captured per device: `modaltrace.gpu.device_index`, `modaltrace.gpu.utilization`, `modaltrace.gpu.memory.used`, `modaltrace.gpu.memory.free`, `modaltrace.gpu.temperature`, `modaltrace.gpu.power.draw`.

```python
with tracer.start_as_current_span("gpu_operation") as span:
    tensor = torch.randn(10000, 10000).cuda()
    result = torch.matmul(tensor, tensor)
    span.set_attribute("matrix_size", 10000)
```

---

## Metrics Collection

```python
from modaltrace import ModalTraceSDK, get_meter
import time

sdk = ModalTraceSDK()
sdk.start()

meter = get_meter(__name__)

frame_latency = meter.create_histogram("frame.latency", unit="ms")
frames_processed = meter.create_counter("frames.processed")
queue_size = meter.create_gauge("processing.queue_size")

for frame in frame_stream:
    start = time.time()
    process_frame(frame)

    frame_latency.record((time.time() - start) * 1000)
    frames_processed.add(1)
    queue_size.set(get_queue_size())
```

---

## Structured Logging

Logs are automatically correlated with the active span's trace context.

```python
from modaltrace.logging import info, error, warning, debug
from modaltrace import get_tracer

tracer = get_tracer(__name__)

def process_batch(batch_id, batch_data):
    with tracer.start_as_current_span("batch_processing"):
        info("Processing batch", batch_id=batch_id, size=len(batch_data))

        try:
            results = [process_item(item) for item in batch_data]
            info("Batch completed", batch_id=batch_id, items_processed=len(results))
            return results
        except Exception as e:
            error("Batch failed", batch_id=batch_id, error=str(e), error_type=type(e).__name__)
            raise
```

---

## Audio/Video Synchronization

```python
from modaltrace import ModalTraceSDK, get_tracer
from modaltrace.conventions.attributes import AVSyncAttributes
import time

sdk = ModalTraceSDK()
sdk.start()

tracer = get_tracer(__name__)

def process_av_stream():
    audio_chunks = {}

    with tracer.start_as_current_span("av_pipeline"):
        audio_chunk_id = 100
        audio_chunks[audio_chunk_id] = time.time()

        video_timestamp = time.time()
        drift_ms = (video_timestamp - audio_chunks[audio_chunk_id]) * 1000

        with tracer.start_as_current_span("av_sync") as sync_span:
            sync_span.set_attribute(AVSyncAttributes.CHUNK_ID, audio_chunk_id)
            sync_span.set_attribute(AVSyncAttributes.DRIFT_MS, drift_ms)

            if abs(drift_ms) > 40:
                warning("A/V sync drift detected", drift_ms=drift_ms)
```

---

## Error Handling

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
    except Exception as e:
        span.record_exception(e)
        span.set_status(Status(StatusCode.ERROR, description=str(e)))
        raise
```

---

## PII Scrubbing

```python
config = ModalTraceConfig(
    scrubbing_enabled=True,
    scrubbing_patterns=[
        r'\b\d{3}-\d{2}-\d{4}\b',                           # SSN
        r'\b\d{16}\b',                                        # Credit card
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b',  # Email
    ]
)
```

---

## Async Operations

```python
import asyncio
from modaltrace import get_tracer

tracer = get_tracer(__name__)

async def async_operation():
    with tracer.start_as_current_span("async_op") as span:
        result = await some_async_work()
        span.set_attribute("result", result)
        return result

async def main():
    with tracer.start_as_current_span("main"):
        results = await asyncio.gather(
            async_operation(),
            async_operation(),
            async_operation(),
        )

asyncio.run(main())
```

---

## Custom Span Processors

```python
from opentelemetry.sdk.trace import SpanProcessor
from opentelemetry.trace import Span
from opentelemetry import trace

class LoggingSpanProcessor(SpanProcessor):
    def on_start(self, span: Span, parent_context) -> None:
        print(f"Span started: {span.name}")

    def on_end(self, span: Span) -> None:
        print(f"Span ended: {span.name} ({span.end_time - span.start_time}ns)")

    def shutdown(self) -> None: pass
    def force_flush(self, timeout_millis: int = 30000) -> bool: return True

sdk = ModalTraceSDK()
sdk.start()
trace.get_tracer_provider().add_span_processor(LoggingSpanProcessor())
```

---

## Full Example: Video Processing Pipeline

```python
import asyncio
import time
from modaltrace import ModalTraceSDK, ModalTraceConfig, get_tracer, get_meter
from modaltrace.logging import info, error
from modaltrace.conventions.attributes import PipelineAttributes, InferenceAttributes

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

frame_latency = meter.create_histogram("pipeline.frame.latency", unit="ms")
frames_processed = meter.create_counter("pipeline.frames.processed")

async def process_video_stream(video_file):
    with tracer.start_as_current_span("video_processing") as span:
        span.set_attribute("video_file", video_file)
        info("Starting video processing", video_file=video_file)

        frame_count = 0
        try:
            for frame_id, frame in enumerate(load_frames(video_file)):
                with tracer.start_as_current_span("process_frame") as frame_span:
                    start = time.time()
                    frame_span.set_attribute(PipelineAttributes.FRAME_SEQ, frame_id)

                    with tracer.start_as_current_span("preprocess"):
                        frame = preprocess(frame)

                    with tracer.start_as_current_span("inference") as infer_span:
                        result = model(frame)
                        infer_span.set_attribute(InferenceAttributes.FORWARD_PASS_MS, 12.5)

                    with tracer.start_as_current_span("postprocess"):
                        output = postprocess(result)

                    frame_latency.record((time.time() - start) * 1000)
                    frames_processed.add(1)
                    frame_count += 1

            info("Video processing completed", frames_processed=frame_count)

        except Exception as e:
            error("Video processing failed", error=str(e), frames_processed=frame_count)
            raise

if __name__ == "__main__":
    try:
        asyncio.run(process_video_stream("video.mp4"))
    finally:
        sdk.shutdown()
```

---

## Dashboard Integration

```python
from modaltrace import ModalTraceSDK, ModalTraceConfig, get_tracer
from modaltrace.dashboard import DashboardServer

dashboard = DashboardServer()
dashboard.start()  # UI at http://localhost:8000, OTLP receiver at http://localhost:4318

config = ModalTraceConfig(
    service_name="my-pipeline",
    otlp_endpoint="http://localhost:4318",
    pytorch_instrumentation=True,
    gpu_monitoring=True,
)

sdk = ModalTraceSDK(config)
sdk.start()

with tracer.start_as_current_span("main") as span:
    span.set_attribute("modaltrace.pipeline.frame.sequence_number", 0)
```

For the dashboard to display all stat panels, emit these metrics with the specified attributes:

```python
pipeline_latency = meter.create_histogram("modaltrace.pipeline.stage.duration", unit="ms")
dropped_frames = meter.create_counter("modaltrace.frames.dropped")
av_drift = meter.create_gauge("modaltrace.av_sync.drift", unit="ms")

# Record per-stage latency with the stage attribute
pipeline_latency.record(latency, attributes={"modaltrace.pipeline.stage": "inference"})
pipeline_latency.record(latency, attributes={"modaltrace.pipeline.stage": "render"})
pipeline_latency.record(latency, attributes={"modaltrace.pipeline.stage": "encode"})
```

---

For full API details, see [API.md](./API.md).
