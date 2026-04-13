"""
middleware/logging_middleware.py
--------------------------------
Attaches before/after request hooks to log every HTTP request and its
outcome to stdout in a structured format.

Registered via register_logging_middleware(app) in app.py.
"""

import time
import logging
from flask import Flask, request, g

logger = logging.getLogger("kba.access")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


def register_logging_middleware(app: Flask) -> None:
    """Attach before/after-request hooks to *app*."""

    @app.before_request
    def _start_timer():
        g.start_time = time.perf_counter()

    @app.after_request
    def _log_request(response):
        elapsed_ms = (time.perf_counter() - g.get("start_time", time.perf_counter())) * 1000
        logger.info(
            "%s %s %s %.1fms — %s",
            request.method,
            request.path,
            request.remote_addr,
            elapsed_ms,
            response.status,
        )
        return response
