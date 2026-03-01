"""OTLP exporter and provider setup.

Configures TracerProvider, MeterProvider, and LoggerProvider with OTLP
HTTP or gRPC exporters based on ModalTraceConfig.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

if TYPE_CHECKING:
    from modaltrace.config import ModalTraceConfig


def create_resource(config: ModalTraceConfig) -> Resource:
    return Resource.create(
        {
            "service.name": config.service_name,
            "service.version": config.service_version,
            "deployment.environment": config.deployment_environment,
        }
    )


def setup_tracer_provider(
    config: ModalTraceConfig, resource: Resource
) -> tuple[TracerProvider, Any]:
    provider = TracerProvider(resource=resource)
    exporter = _create_span_exporter(config)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    return provider, exporter


def setup_meter_provider(config: ModalTraceConfig, resource: Resource):
    from opentelemetry import metrics
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader

    exporter = _create_metric_exporter(config)
    reader = PeriodicExportingMetricReader(
        exporter,
        export_interval_millis=config.metrics_flush_interval_ms,
    )
    provider = MeterProvider(resource=resource, metric_readers=[reader])
    metrics.set_meter_provider(provider)
    return provider


def setup_logger_provider(config: ModalTraceConfig, resource: Resource):
    from opentelemetry.sdk._logs import LoggerProvider
    from opentelemetry.sdk._logs.export import BatchLogRecordProcessor

    exporter = _create_log_exporter(config)
    provider = LoggerProvider(resource=resource)
    provider.add_log_record_processor(BatchLogRecordProcessor(exporter))
    return provider


def _create_span_exporter(config: ModalTraceConfig):
    endpoint = str(config.otlp_endpoint).rstrip("/")
    headers = config.otlp_headers
    timeout = config.otlp_timeout_ms // 1000

    if config.otlp_protocol == "grpc":
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

        return OTLPSpanExporter(
            endpoint=endpoint,
            headers=tuple(headers.items()) if headers else None,
            timeout=timeout,
        )
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

    return OTLPSpanExporter(
        endpoint=f"{endpoint}/v1/traces",
        headers=headers,
        timeout=timeout,
    )


def _create_metric_exporter(config: ModalTraceConfig):
    endpoint = str(config.otlp_endpoint).rstrip("/")
    headers = config.otlp_headers
    timeout = config.otlp_timeout_ms // 1000

    if config.otlp_protocol == "grpc":
        from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter

        return OTLPMetricExporter(
            endpoint=endpoint,
            headers=tuple(headers.items()) if headers else None,
            timeout=timeout,
        )
    from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter

    return OTLPMetricExporter(
        endpoint=f"{endpoint}/v1/metrics",
        headers=headers,
        timeout=timeout,
    )


def _create_log_exporter(config: ModalTraceConfig):
    endpoint = str(config.otlp_endpoint).rstrip("/")
    headers = config.otlp_headers
    timeout = config.otlp_timeout_ms // 1000

    if config.otlp_protocol == "grpc":
        from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter

        return OTLPLogExporter(
            endpoint=endpoint,
            headers=tuple(headers.items()) if headers else None,
            timeout=timeout,
        )
    from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter

    return OTLPLogExporter(
        endpoint=f"{endpoint}/v1/logs",
        headers=headers,
        timeout=timeout,
    )
