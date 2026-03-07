"""Entry point for running the ModalTrace dashboard."""

import logging
import uvicorn

logger = logging.getLogger(__name__)


def main():
    """Run the dashboard server."""
    logger.info("ModalTrace Dashboard running at http://localhost:4318")
    uvicorn.run(
        "modaltrace.dashboard.server:app",
        host="0.0.0.0",
        port=4318,
        log_level="info",
    )


if __name__ == "__main__":
    main()
