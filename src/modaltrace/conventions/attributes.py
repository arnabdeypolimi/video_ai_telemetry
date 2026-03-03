"""Semantic convention string constants for modaltrace.

All attribute keys live here — zero magic strings in the rest of the codebase.
"""


class PipelineAttributes:
    ID = "modaltrace.pipeline.id"
    SESSION_ID = "modaltrace.pipeline.session_id"
    STAGE_NAME = "modaltrace.pipeline.stage.name"
    STAGE_DURATION_MS = "modaltrace.pipeline.stage.duration_ms"
    FRAME_SEQ = "modaltrace.pipeline.frame.sequence_number"
    TARGET_FPS = "modaltrace.pipeline.target_fps"
    SPAN_PENDING = "modaltrace.span.pending"


class InferenceAttributes:
    MODEL_NAME = "modaltrace.inference.model_name"
    FORWARD_PASS_MS = "modaltrace.inference.forward_pass_ms"
    BATCH_SIZE = "modaltrace.inference.batch_size"
    GPU_MEMORY_MB = "modaltrace.inference.gpu.memory_allocated_mb"
    GPU_MEMORY_DELTA_MB = "modaltrace.inference.gpu.memory_delta_mb"
    INPUT_SHAPES = "modaltrace.inference.input_shapes"
    DEVICE = "modaltrace.inference.device"


class ModalAttributes:
    FLAME_INFERENCE_MS = "modaltrace.flame.inference_ms"
    FLAME_PARAM_COUNT = "modaltrace.flame.parameter_count"
    RENDER_FRAME_MS = "modaltrace.render.frame_ms"
    RENDER_RESOLUTION = "modaltrace.render.resolution"
    MESH_VERTEX_COUNT = "modaltrace.mesh.vertex_count"
    FRAME_SEQ = "modaltrace.frame.sequence_number"


class AVSyncAttributes:
    DRIFT_MS = "modaltrace.av_sync.drift_ms"
    JITTER_MS = "modaltrace.av_sync.jitter_ms"
    THRESHOLD_MS = "modaltrace.av_sync.threshold_ms"
    UNMATCHED_CHUNKS = "modaltrace.av_sync.unmatched_chunks"
    CHUNK_ID = "modaltrace.av_sync.chunk_id"


class GPUAttributes:
    DEVICE_INDEX = "modaltrace.gpu.device_index"
    DEVICE_NAME = "modaltrace.gpu.device_name"
    UTILIZATION_PCT = "modaltrace.gpu.utilization"
    MEMORY_USED_MB = "modaltrace.gpu.memory.used"
    MEMORY_FREE_MB = "modaltrace.gpu.memory.free"
    TEMPERATURE_C = "modaltrace.gpu.temperature"
    POWER_W = "modaltrace.gpu.power.draw"


class TransportAttributes:
    PROTOCOL = "modaltrace.transport.protocol"
    RTT_MS = "modaltrace.transport.rtt_ms"
    JITTER_MS = "modaltrace.transport.jitter_ms"
    PACKET_LOSS_PCT = "modaltrace.transport.packet_loss_percent"
    BITRATE_KBPS = "modaltrace.transport.bitrate_kbps"
    FRAME_RATE_ACTUAL = "modaltrace.transport.frame_rate_actual"
    STREAM = "modaltrace.transport.stream"


class EventLoopAttributes:
    ELAPSED_MS = "modaltrace.eventloop.blocked_ms"
    THRESHOLD_MS = "modaltrace.eventloop.threshold_ms"
    HANDLE_CALLBACK = "modaltrace.eventloop.handle_callback"
