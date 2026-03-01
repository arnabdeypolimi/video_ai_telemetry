"""Structured log API for modaltrace.

Provides module-level log functions (trace, debug, info, notice, warning, error, exception)
that emit OTel log records with structured attributes. Each record automatically carries
the current OTel trace context (trace_id, span_id) for correlation with active spans.

Before init() is called all functions are no-ops — no crash, no output.

f-string template support: a message containing {var} is stored as event_name (queryable
and consistent) while the formatted version with substituted values is stored as the body.

Level filtering: log records below the configured log_level threshold are dropped at emit
time without any OTel SDK call.

Console output: when log_console=True (the default), log records are also printed to stdout.
"""

from __future__ import annotations

import sys
import time
import traceback
from typing import TYPE_CHECKING, Any

from opentelemetry import context as otel_context
from opentelemetry import trace
from opentelemetry._logs import set_logger_provider
from opentelemetry._logs.severity import SeverityNumber
from opentelemetry.sdk._logs import LoggerProvider

if TYPE_CHECKING:
    from opentelemetry.sdk._logs import Logger  # type: ignore[attr-defined]

# ---------------------------------------------------------------------------
# Severity mapping
# ---------------------------------------------------------------------------

_LEVEL_MAP: dict[str, SeverityNumber] = {
    "trace": SeverityNumber.TRACE,
    "debug": SeverityNumber.DEBUG,
    "info": SeverityNumber.INFO,
    "warning": SeverityNumber.WARN,
    "error": SeverityNumber.ERROR,
}

# Map each public function name to its OTel severity number.
_SEVERITY_MAP: dict[str, tuple[SeverityNumber, str]] = {
    "trace": (SeverityNumber.TRACE, "TRACE"),
    "debug": (SeverityNumber.DEBUG, "DEBUG"),
    "info": (SeverityNumber.INFO, "INFO"),
    "notice": (SeverityNumber.WARN, "NOTICE"),  # 13 — WARN per spec
    "warning": (SeverityNumber.WARN, "WARN"),
    "error": (SeverityNumber.ERROR, "ERROR"),
    "exception": (SeverityNumber.ERROR, "ERROR"),
}

# ---------------------------------------------------------------------------
# Module-level state
# ---------------------------------------------------------------------------

# Set by _init_logging() during modaltrace.init().  None = before init.
_logger: Logger | None = None
_min_severity: SeverityNumber = SeverityNumber.INFO
_log_console: bool = False


def _init_logging(
    logger_provider: LoggerProvider,
    log_level: str = "info",
    log_console: bool = False,
) -> None:
    """Called once during modaltrace.init() to wire up the module-level logger.

    Parameters
    ----------
    logger_provider:
        The SDK LoggerProvider that has been configured with processors/exporters.
    log_level:
        Minimum severity level string (e.g. "debug", "info", "warning", "error").
        Records below this level are silently dropped.
    log_console:
        When True, log records are also printed to stdout.
    """
    global _logger, _min_severity, _log_console

    set_logger_provider(logger_provider)
    _logger = logger_provider.get_logger(
        "modaltrace",
        schema_url="https://opentelemetry.io/schemas/1.24.0",
    )
    _min_severity = _LEVEL_MAP.get(log_level.lower(), SeverityNumber.INFO)
    _log_console = log_console


# ---------------------------------------------------------------------------
# Core emit helper
# ---------------------------------------------------------------------------


def _emit(
    level: str,
    msg: str,
    exc_info: bool = False,
    **attrs: Any,
) -> None:
    """Internal emit — shared by all public functions.

    Parameters
    ----------
    level:
        One of "trace", "debug", "info", "notice", "warning", "error", "exception".
    msg:
        The log message.  May contain {key} placeholders which will be formatted
        using *attrs* to produce the human-readable body.  The original template
        string is stored as the OTel event_name for consistent querying.
    exc_info:
        When True the current exception (if any) is captured and appended to attrs.
    attrs:
        Arbitrary keyword arguments that become structured OTel log attributes.
    """
    if _logger is None:
        # Before init() — silently discard.
        return

    severity_number, severity_text = _SEVERITY_MAP.get(level, (SeverityNumber.INFO, "INFO"))

    # Level filtering — drop records below the configured threshold.
    if severity_number.value < _min_severity.value:
        return

    # f-string template: store original template as event_name, formatted as body.
    event_name = msg
    try:
        body = msg.format(**attrs)
    except (KeyError, ValueError):
        body = msg

    # Build a flat attributes dict — all user kwargs, plus exc_info if requested.
    log_attrs: dict[str, Any] = dict(attrs)

    if exc_info:
        exc_type, exc_value, exc_tb = sys.exc_info()
        if exc_value is not None:
            log_attrs["exception.type"] = exc_type.__name__ if exc_type is not None else "unknown"
            log_attrs["exception.message"] = str(exc_value)
            log_attrs["exception.stacktrace"] = "".join(
                traceback.format_exception(exc_type, exc_value, exc_tb)
            )

    # Retrieve the current OTel span context so the log record is correlated.
    current_span = trace.get_current_span()
    span_ctx = current_span.get_span_context()

    # Emit via the OTel Logger.emit() keyword interface.
    _logger.emit(
        timestamp=time.time_ns(),
        context=otel_context.get_current(),
        severity_number=severity_number,
        severity_text=severity_text,
        body=body,
        event_name=event_name,
        attributes=log_attrs if log_attrs else None,
    )

    # Optional console output.
    if _log_console:
        trace_hex = format(span_ctx.trace_id, "032x") if span_ctx.is_valid else "0" * 32
        span_hex = format(span_ctx.span_id, "016x") if span_ctx.is_valid else "0" * 16
        print(
            f"[{severity_text}] {body} (trace={trace_hex[:8]}… span={span_hex[:8]}…)",
            file=sys.stdout,
        )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def trace_log(msg: str, **attrs: Any) -> None:
    """Emit a TRACE-severity OTel log record."""
    _emit("trace", msg, **attrs)


def debug(msg: str, **attrs: Any) -> None:
    """Emit a DEBUG-severity OTel log record."""
    _emit("debug", msg, **attrs)


def info(msg: str, **attrs: Any) -> None:
    """Emit an INFO-severity OTel log record."""
    _emit("info", msg, **attrs)


def notice(msg: str, **attrs: Any) -> None:
    """Emit a NOTICE-severity OTel log record (severity=WARN/13)."""
    _emit("notice", msg, **attrs)


def warning(msg: str, **attrs: Any) -> None:
    """Emit a WARN-severity OTel log record."""
    _emit("warning", msg, **attrs)


def error(msg: str, **attrs: Any) -> None:
    """Emit an ERROR-severity OTel log record."""
    _emit("error", msg, **attrs)


def exception(msg: str, **attrs: Any) -> None:
    """Emit an ERROR-severity OTel log record capturing the current exception."""
    _emit("exception", msg, exc_info=True, **attrs)


# Expose trace under the name `trace` as well (avoids collision with the `trace`
# module at the top level — callers use modaltrace.trace, not this module directly).
trace_log.__name__ = "trace"
