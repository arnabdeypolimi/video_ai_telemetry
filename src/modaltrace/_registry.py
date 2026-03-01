"""Module-level singletons for the modaltrace SDK.

Holds references to the active config, providers, and components
so that module-level functions (pipeline_stage, info, etc.) can
access them without requiring the user to pass the SDK instance.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from modaltrace.config import ModalTraceConfig

_config: ModalTraceConfig | None = None
_tracer = None
_meter = None
_logger_provider = None
_sdk = None


def get_config() -> ModalTraceConfig:
    if _config is None:
        raise RuntimeError("modaltrace.init() has not been called yet")
    return _config
