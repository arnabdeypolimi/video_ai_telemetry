"""Tests for the structured log API (logging/api.py).

Validates:
- info / warning / error emit log records with the correct OTel severity numbers
- kwargs become structured attributes on the emitted log record
- Level filtering: debug records are silently dropped when min_level=info
- All public functions are no-ops before _init_logging() is called (no crash)
- f-string template: body is formatted, event_name is the original template
- exception() captures current exception details into attributes
"""

from __future__ import annotations

import avatar_otel.logging.api as log_api
import pytest
from opentelemetry._logs.severity import SeverityNumber
from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk._logs.export import InMemoryLogRecordExporter, SimpleLogRecordProcessor


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_provider() -> tuple[LoggerProvider, InMemoryLogRecordExporter]:
    """Return a (LoggerProvider, exporter) pair wired together."""
    exporter = InMemoryLogRecordExporter()
    provider = LoggerProvider()
    provider.add_log_record_processor(SimpleLogRecordProcessor(exporter))
    return provider, exporter


def _get_records(exporter: InMemoryLogRecordExporter):
    """Return the list of log records captured so far."""
    return [r.log_record for r in exporter.get_finished_logs()]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_logger():
    """Reset module-level logger state before and after each test."""
    # Capture original state
    orig_logger = log_api._logger
    orig_severity = log_api._min_severity
    orig_console = log_api._log_console

    # Reset to pre-init state
    log_api._logger = None
    log_api._min_severity = SeverityNumber.INFO
    log_api._log_console = False

    yield

    # Restore original state
    log_api._logger = orig_logger
    log_api._min_severity = orig_severity
    log_api._log_console = orig_console


@pytest.fixture
def logging_setup():
    """Initialise the logging module with an in-memory exporter at INFO level."""
    provider, exporter = _make_provider()
    log_api._init_logging(provider, log_level="info", log_console=False)
    return exporter


# ---------------------------------------------------------------------------
# 1. Basic severity tests
# ---------------------------------------------------------------------------


class TestSeverityLevels:
    def test_info_emits_info_severity(self, logging_setup):
        exporter = logging_setup
        log_api.info("hello world")
        records = _get_records(exporter)
        assert len(records) == 1
        assert records[0].severity_number == SeverityNumber.INFO

    def test_warning_emits_warn_severity(self, logging_setup):
        exporter = logging_setup
        log_api.warning("something looks off")
        records = _get_records(exporter)
        assert len(records) == 1
        assert records[0].severity_number == SeverityNumber.WARN

    def test_error_emits_error_severity(self, logging_setup):
        exporter = logging_setup
        log_api.error("something broke")
        records = _get_records(exporter)
        assert len(records) == 1
        assert records[0].severity_number == SeverityNumber.ERROR

    def test_notice_emits_warn_severity(self, logging_setup):
        """notice() maps to WARN (value 13) per the OTel spec."""
        exporter = logging_setup
        log_api.notice("note this")
        records = _get_records(exporter)
        assert len(records) == 1
        assert records[0].severity_number == SeverityNumber.WARN

    def test_debug_emits_debug_severity_when_level_is_debug(self):
        """debug() records are emitted when min_level=debug."""
        provider, exporter = _make_provider()
        log_api._init_logging(provider, log_level="debug", log_console=False)
        log_api.debug("debug detail")
        records = _get_records(exporter)
        assert len(records) == 1
        assert records[0].severity_number == SeverityNumber.DEBUG

    def test_exception_emits_error_severity(self, logging_setup):
        exporter = logging_setup
        try:
            raise ValueError("oops")
        except ValueError:
            log_api.exception("caught an error")
        records = _get_records(exporter)
        assert len(records) == 1
        assert records[0].severity_number == SeverityNumber.ERROR


# ---------------------------------------------------------------------------
# 2. Structured attributes
# ---------------------------------------------------------------------------


class TestStructuredAttributes:
    def test_kwargs_become_attributes(self, logging_setup):
        exporter = logging_setup
        log_api.info("pipeline started", session_id="abc123", target_fps=30)
        records = _get_records(exporter)
        assert len(records) == 1
        attrs = records[0].attributes
        assert attrs is not None
        assert attrs["session_id"] == "abc123"
        assert attrs["target_fps"] == 30

    def test_no_kwargs_produces_no_attributes(self, logging_setup):
        exporter = logging_setup
        log_api.info("simple message")
        records = _get_records(exporter)
        assert len(records) == 1
        # attributes should be None or an empty mapping
        attrs = records[0].attributes
        assert not attrs  # None or empty dict both falsy

    def test_multiple_kwarg_types(self, logging_setup):
        exporter = logging_setup
        log_api.warning("drift exceeded", drift_ms=47.3, chunk_id=1024, flag=True)
        records = _get_records(exporter)
        attrs = records[0].attributes
        assert attrs["drift_ms"] == pytest.approx(47.3)
        assert attrs["chunk_id"] == 1024
        assert attrs["flag"] is True


# ---------------------------------------------------------------------------
# 3. Level filtering
# ---------------------------------------------------------------------------


class TestLevelFiltering:
    def test_debug_filtered_when_min_level_is_info(self, logging_setup):
        """debug() records are dropped when the configured level is info."""
        exporter = logging_setup
        log_api.debug("this should be dropped")
        records = _get_records(exporter)
        assert len(records) == 0

    def test_trace_filtered_when_min_level_is_info(self, logging_setup):
        exporter = logging_setup
        log_api.trace_log("trace noise")
        records = _get_records(exporter)
        assert len(records) == 0

    def test_info_passes_when_min_level_is_info(self, logging_setup):
        exporter = logging_setup
        log_api.info("this should pass")
        records = _get_records(exporter)
        assert len(records) == 1

    def test_warning_passes_when_min_level_is_info(self, logging_setup):
        exporter = logging_setup
        log_api.warning("warning passes")
        records = _get_records(exporter)
        assert len(records) == 1

    def test_error_filtered_when_min_level_is_error(self):
        """warning() is dropped when min_level=error."""
        provider, exporter = _make_provider()
        log_api._init_logging(provider, log_level="error", log_console=False)
        log_api.warning("this warning should be dropped")
        records = _get_records(exporter)
        assert len(records) == 0

    def test_error_passes_when_min_level_is_error(self):
        provider, exporter = _make_provider()
        log_api._init_logging(provider, log_level="error", log_console=False)
        log_api.error("this error should pass")
        records = _get_records(exporter)
        assert len(records) == 1


# ---------------------------------------------------------------------------
# 4. No-op before init()
# ---------------------------------------------------------------------------


class TestNoOpBeforeInit:
    """All public functions must be silent no-ops before _init_logging() is called."""

    def test_info_before_init_does_not_crash(self):
        log_api.info("before init")  # Should not raise

    def test_debug_before_init_does_not_crash(self):
        log_api.debug("before init")

    def test_warning_before_init_does_not_crash(self):
        log_api.warning("before init")

    def test_error_before_init_does_not_crash(self):
        log_api.error("before init")

    def test_exception_before_init_does_not_crash(self):
        try:
            raise RuntimeError("test")
        except RuntimeError:
            log_api.exception("before init")  # Should not raise

    def test_notice_before_init_does_not_crash(self):
        log_api.notice("before init")

    def test_trace_before_init_does_not_crash(self):
        log_api.trace_log("before init")


# ---------------------------------------------------------------------------
# 5. f-string template support
# ---------------------------------------------------------------------------


class TestFStringTemplate:
    def test_body_is_formatted(self, logging_setup):
        exporter = logging_setup
        chunk_id = 42
        log_api.info("processing chunk {chunk_id}", chunk_id=chunk_id)
        records = _get_records(exporter)
        assert records[0].body == "processing chunk 42"

    def test_event_name_is_original_template(self, logging_setup):
        exporter = logging_setup
        log_api.info("processing chunk {chunk_id}", chunk_id=42)
        records = _get_records(exporter)
        # event_name should hold the un-formatted template string
        assert records[0].event_name == "processing chunk {chunk_id}"

    def test_missing_placeholder_key_falls_back_gracefully(self, logging_setup):
        """If a placeholder has no matching kwarg, the raw template is used as body."""
        exporter = logging_setup
        log_api.info("hello {missing_key}")
        records = _get_records(exporter)
        # Should not raise; body falls back to the template string
        assert records[0].body == "hello {missing_key}"


# ---------------------------------------------------------------------------
# 6. exception() captures exc_info
# ---------------------------------------------------------------------------


class TestExceptionCapture:
    def test_exception_captures_type(self, logging_setup):
        exporter = logging_setup
        try:
            raise TypeError("bad type")
        except TypeError:
            log_api.exception("caught")
        records = _get_records(exporter)
        attrs = records[0].attributes
        assert attrs is not None
        assert attrs["exception.type"] == "TypeError"

    def test_exception_captures_message(self, logging_setup):
        exporter = logging_setup
        try:
            raise ValueError("something wrong")
        except ValueError:
            log_api.exception("error occurred")
        records = _get_records(exporter)
        attrs = records[0].attributes
        assert "something wrong" in attrs["exception.message"]

    def test_exception_captures_stacktrace(self, logging_setup):
        exporter = logging_setup
        try:
            raise RuntimeError("boom")
        except RuntimeError:
            log_api.exception("pipeline failed")
        records = _get_records(exporter)
        attrs = records[0].attributes
        assert "Traceback" in attrs["exception.stacktrace"]

    def test_exception_without_active_exception_does_not_crash(self, logging_setup):
        """exception() called outside of an except block should not crash."""
        exporter = logging_setup
        log_api.exception("no active exc")
        records = _get_records(exporter)
        # Record emitted but no exception attrs attached
        assert len(records) == 1
        attrs = records[0].attributes or {}
        assert "exception.type" not in attrs


# ---------------------------------------------------------------------------
# 7. Console output (log_console=True)
# ---------------------------------------------------------------------------


class TestConsoleOutput:
    def test_log_console_prints_to_stdout(self, capsys):
        """When log_console=True the formatted message is printed to stdout."""
        provider, exporter = _make_provider()
        log_api._init_logging(provider, log_level="info", log_console=True)
        log_api.info("console message", key="val")
        captured = capsys.readouterr()
        assert "console message" in captured.out
        assert "INFO" in captured.out

    def test_log_console_false_produces_no_stdout(self, capsys, logging_setup):
        """When log_console=False nothing is printed to stdout."""
        log_api.info("silent message")
        captured = capsys.readouterr()
        assert captured.out == ""
