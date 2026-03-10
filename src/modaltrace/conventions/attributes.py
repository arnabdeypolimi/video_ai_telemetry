"""Semantic convention string constants for modaltrace.

All attribute keys live here — zero magic strings in the rest of the codebase.
"""

from modaltrace.conventions.namespaces import NAMESPACE as _NS


class PipelineAttributes:
    ID = f"{_NS}.pipeline.id"
    SESSION_ID = f"{_NS}.pipeline.session_id"
    STAGE_NAME = f"{_NS}.pipeline.stage.name"
    STAGE_DURATION_MS = f"{_NS}.pipeline.stage.duration_ms"
    FRAME_SEQ = f"{_NS}.pipeline.frame.sequence_number"
    TARGET_FPS = f"{_NS}.pipeline.target_fps"
    SPAN_PENDING = f"{_NS}.span.pending"


class InferenceAttributes:
    MODEL_NAME = f"{_NS}.inference.model_name"
    FORWARD_PASS_MS = f"{_NS}.inference.forward_pass_ms"
    BATCH_SIZE = f"{_NS}.inference.batch_size"
    GPU_MEMORY_MB = f"{_NS}.inference.gpu.memory_allocated_mb"
    GPU_MEMORY_DELTA_MB = f"{_NS}.inference.gpu.memory_delta_mb"
    INPUT_SHAPES = f"{_NS}.inference.input_shapes"
    DEVICE = f"{_NS}.inference.device"


class ModalAttributes:
    FLAME_INFERENCE_MS = f"{_NS}.flame.inference_ms"
    FLAME_PARAM_COUNT = f"{_NS}.flame.parameter_count"
    RENDER_FRAME_MS = f"{_NS}.render.frame_ms"
    RENDER_RESOLUTION = f"{_NS}.render.resolution"
    MESH_VERTEX_COUNT = f"{_NS}.mesh.vertex_count"
    FRAME_SEQ = f"{_NS}.frame.sequence_number"


class AVSyncAttributes:
    DRIFT_MS = f"{_NS}.av_sync.drift_ms"
    JITTER_MS = f"{_NS}.av_sync.jitter_ms"
    THRESHOLD_MS = f"{_NS}.av_sync.threshold_ms"
    UNMATCHED_CHUNKS = f"{_NS}.av_sync.unmatched_chunks"
    CHUNK_ID = f"{_NS}.av_sync.chunk_id"


class GPUAttributes:
    DEVICE_INDEX = f"{_NS}.gpu.device_index"
    DEVICE_NAME = f"{_NS}.gpu.device_name"
    UTILIZATION_PCT = f"{_NS}.gpu.utilization"
    MEMORY_USED_MB = f"{_NS}.gpu.memory.used"
    MEMORY_FREE_MB = f"{_NS}.gpu.memory.free"
    TEMPERATURE_C = f"{_NS}.gpu.temperature"
    POWER_W = f"{_NS}.gpu.power.draw"


class TransportAttributes:
    PROTOCOL = f"{_NS}.transport.protocol"
    RTT_MS = f"{_NS}.transport.rtt_ms"
    JITTER_MS = f"{_NS}.transport.jitter_ms"
    PACKET_LOSS_PCT = f"{_NS}.transport.packet_loss_percent"
    BITRATE_KBPS = f"{_NS}.transport.bitrate_kbps"
    FRAME_RATE_ACTUAL = f"{_NS}.transport.frame_rate_actual"
    STREAM = f"{_NS}.transport.stream"


class EventLoopAttributes:
    ELAPSED_MS = f"{_NS}.eventloop.blocked_ms"
    THRESHOLD_MS = f"{_NS}.eventloop.threshold_ms"
    HANDLE_CALLBACK = f"{_NS}.eventloop.handle_callback"
