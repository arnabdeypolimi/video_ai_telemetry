"""ModalTrace observability dashboard."""

__all__ = ["DashboardServer", "TelemetryStore"]

import threading

import uvicorn

from .server import app
from .store import TelemetryStore


class DashboardServer:
    """Runs the ModalTrace dashboard (OTLP receiver + web UI) on a single port."""

    def __init__(self, host: str = "0.0.0.0", port: int = 8000):
        self.host = host
        self.port = port
        self._thread: threading.Thread | None = None

    def start(self, blocking: bool = False) -> None:
        """Start the dashboard server.

        Args:
            blocking: If True, run in the current thread (blocks). If False,
                      run in a background daemon thread.
        """
        if blocking:
            self._run()
        else:
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()

    def _run(self) -> None:
        uvicorn.run(app, host=self.host, port=self.port, log_level="info")
