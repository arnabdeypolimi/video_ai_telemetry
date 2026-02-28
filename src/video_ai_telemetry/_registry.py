"""Module-level singletons for the video-ai-telemetry SDK.

Holds references to the active config, providers, and components
so that module-level functions (pipeline_stage, info, etc.) can
access them without requiring the user to pass the SDK instance.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from video_ai_telemetry.config import AvatarOtelConfig

_config: AvatarOtelConfig | None = None
_tracer = None
_meter = None
_logger_provider = None
_sdk = None


def get_config() -> AvatarOtelConfig:
    if _config is None:
        raise RuntimeError("video_ai_telemetry.init() has not been called yet")
    return _config
