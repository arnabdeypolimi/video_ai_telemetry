"""FastAPI server for OTLP receiver and telemetry dashboard API."""

import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.requests import Request

from .proto_parser import parse_logs_request, parse_metrics_request, parse_traces_request
from .store import TelemetryStore

logger = logging.getLogger(__name__)

# Global singleton store
store = TelemetryStore()

app = FastAPI(title="ModalTrace Dashboard")


# OTLP receiver endpoints
@app.post("/v1/traces")
async def receive_traces(request: Request):
    """Receive OTLP TracesData."""
    try:
        body = await request.body()
        spans = parse_traces_request(body)
        for span in spans:
            store.add_span(span)
    except Exception as e:
        logger.exception("Error parsing traces: %s", e)
    return {}


@app.post("/v1/metrics")
async def receive_metrics(request: Request):
    """Receive OTLP MetricsData."""
    try:
        body = await request.body()
        metric_points = parse_metrics_request(body)
        for point in metric_points:
            store.add_metric_point(point)
    except Exception as e:
        logger.exception("Error parsing metrics: %s", e)
    return {}


@app.post("/v1/logs")
async def receive_logs(request: Request):
    """Receive OTLP LogsData."""
    try:
        body = await request.body()
        logs = parse_logs_request(body)
        for log in logs:
            store.add_log(log)
    except Exception as e:
        logger.exception("Error parsing logs: %s", e)
    return {}


# API endpoints
@app.get("/api/spans")
async def get_spans(since_ms: int | None = None, limit: int = 50):
    """Get recent spans."""
    return store.get_spans(since_ms=since_ms, limit=limit)


@app.get("/api/metrics/{name}")
async def get_metrics(name: str, since_ms: int | None = None):
    """Get metric time series by name."""
    # Restore dots: "modaltrace__gpu__utilization" -> "modaltrace.gpu.utilization"
    metric_name = name.replace("__", ".")
    return store.get_metric_series(metric_name, since_ms=since_ms)


@app.get("/api/gpu")
async def get_gpu():
    """Get latest GPU readings."""
    return store.get_latest_gpu()


@app.get("/api/logs")
async def get_logs(since_ms: int | None = None, level: str | None = None, limit: int = 100):
    """Get log records."""
    return store.get_logs(since_ms=since_ms, level=level, limit=limit)


# Serve static files
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
