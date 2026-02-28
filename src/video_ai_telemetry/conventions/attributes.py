"""Semantic convention string constants for video-ai-telemetry.

All attribute keys live here — zero magic strings in the rest of the codebase.
"""


class PipelineAttributes:
    ID = "rt_video.pipeline.id"
    SESSION_ID = "rt_video.pipeline.session_id"
    STAGE_NAME = "rt_video.pipeline.stage.name"
    STAGE_DURATION_MS = "rt_video.pipeline.stage.duration_ms"
    FRAME_SEQ = "rt_video.pipeline.frame.sequence_number"
    TARGET_FPS = "rt_video.pipeline.target_fps"
    SPAN_PENDING = "rt_video.span.pending"


class InferenceAttributes:
    MODEL_NAME = "rt_video.inference.model_name"
    FORWARD_PASS_MS = "rt_video.inference.forward_pass_ms"
    BATCH_SIZE = "rt_video.inference.batch_size"
    GPU_MEMORY_MB = "rt_video.inference.gpu.memory_allocated_mb"
    GPU_MEMORY_DELTA_MB = "rt_video.inference.gpu.memory_delta_mb"
    INPUT_SHAPES = "rt_video.inference.input_shapes"
    DEVICE = "rt_video.inference.device"


class AvatarAttributes:
    FLAME_INFERENCE_MS = "avatar.flame.inference_ms"
    FLAME_PARAM_COUNT = "avatar.flame.parameter_count"
    RENDER_FRAME_MS = "avatar.render.frame_ms"
    RENDER_RESOLUTION = "avatar.render.resolution"
    MESH_VERTEX_COUNT = "avatar.mesh.vertex_count"
    FRAME_SEQ = "avatar.frame.sequence_number"


class AVSyncAttributes:
    DRIFT_MS = "rt_video.av_sync.drift_ms"
    JITTER_MS = "rt_video.av_sync.jitter_ms"
    THRESHOLD_MS = "rt_video.av_sync.threshold_ms"
    UNMATCHED_CHUNKS = "rt_video.av_sync.unmatched_chunks"
    CHUNK_ID = "rt_video.av_sync.chunk_id"


class GPUAttributes:
    DEVICE_INDEX = "rt_video.gpu.device_index"
    UTILIZATION_PCT = "rt_video.gpu.utilization"
    MEMORY_USED_MB = "rt_video.gpu.memory.used"
    MEMORY_FREE_MB = "rt_video.gpu.memory.free"
    TEMPERATURE_C = "rt_video.gpu.temperature"
    POWER_W = "rt_video.gpu.power.draw"


class TransportAttributes:
    PROTOCOL = "rt_video.transport.protocol"
    RTT_MS = "rt_video.transport.rtt_ms"
    JITTER_MS = "rt_video.transport.jitter_ms"
    PACKET_LOSS_PCT = "rt_video.transport.packet_loss_percent"
    BITRATE_KBPS = "rt_video.transport.bitrate_kbps"
    FRAME_RATE_ACTUAL = "rt_video.transport.frame_rate_actual"
    STREAM = "rt_video.transport.stream"


class EventLoopAttributes:
    ELAPSED_MS = "rt_video.eventloop.blocked_ms"
    THRESHOLD_MS = "rt_video.eventloop.threshold_ms"
    HANDLE_CALLBACK = "rt_video.eventloop.handle_callback"
