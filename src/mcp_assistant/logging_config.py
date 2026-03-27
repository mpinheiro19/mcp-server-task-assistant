"""Centralised logging configuration for the MCP assistant server.

Call ``setup_logging()`` once at process startup (before FastMCP initialises).
All configuration is driven by environment variables so that it works both in
development (plain text on stderr) and in production pipelines (JSON).

Environment variables
---------------------
LOG_LEVEL        : DEBUG | INFO | WARNING | ERROR | CRITICAL  (default: INFO)
LOG_FORMAT       : text | json                                 (default: text)
LOG_PREVIEW_CHARS: number of content chars shown at DEBUG      (default: 200)
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from contextlib import contextmanager
from typing import Generator

# ---------------------------------------------------------------------------
# Public constants — importable by other modules that need them
# ---------------------------------------------------------------------------

LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_FORMAT: str = os.getenv("LOG_FORMAT", "text").lower()  # "text" | "json"
LOG_PREVIEW_CHARS: int = int(os.getenv("LOG_PREVIEW_CHARS", "200"))

_TEXT_FORMAT = "%(asctime)s [%(levelname)-5s] %(name)s - %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


# ---------------------------------------------------------------------------
# Formatters
# ---------------------------------------------------------------------------


class JsonFormatter(logging.Formatter):
    """Emit one JSON object per log record (suitable for log aggregation)."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict = {
            "ts": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "module": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------


def setup_logging() -> None:
    """Configure the ``mcp_assistant`` logger hierarchy.

    Must be called once, before FastMCP initialises, so that every module
    logger (``logging.getLogger(__name__)``) inherits the correct handler and
    level without polluting the root logger used by third-party libraries.
    """
    handler = logging.StreamHandler(sys.stderr)
    if LOG_FORMAT == "json":
        handler.setFormatter(JsonFormatter(datefmt=_DATE_FORMAT))
    else:
        handler.setFormatter(logging.Formatter(_TEXT_FORMAT, datefmt=_DATE_FORMAT))

    pkg_logger = logging.getLogger("mcp_assistant")
    pkg_logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))
    # Avoid duplicate handlers when called more than once (e.g. in tests)
    if not pkg_logger.handlers:
        pkg_logger.addHandler(handler)
    pkg_logger.propagate = False

    # Surface FastMCP's own logs only when the user explicitly asked for DEBUG;
    # otherwise they would flood stderr with protocol-level noise.
    logging.getLogger("fastmcp").setLevel(
        logging.DEBUG if LOG_LEVEL == "DEBUG" else logging.WARNING
    )

    pkg_logger.info("logging initialized level=%s format=%s", LOG_LEVEL, LOG_FORMAT)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@contextmanager
def log_operation(
    logger: logging.Logger,
    operation: str,
    **ctx: object,
) -> Generator[None, None, None]:
    """Time-tracking context manager for any significant operation.

    Emits an ``INFO`` line on entry and on successful exit (with elapsed ms),
    or an ``ERROR`` line if an exception propagates out.

    Usage::

        with log_operation(logger, "create_prd", feature=feature_name):
            ...  # do the work

    The ``**ctx`` keyword arguments are appended as ``key=value`` pairs to
    every log line emitted by this context manager, making it easy to
    correlate start/end entries in log streams.
    """
    kv = " ".join(f"{k}={v}" for k, v in ctx.items())
    logger.info("start op=%s %s", operation, kv)
    t0 = time.perf_counter()
    try:
        yield
        ms = int((time.perf_counter() - t0) * 1000)
        logger.info("end op=%s status=ok duration=%dms %s", operation, ms, kv)
    except Exception as exc:
        ms = int((time.perf_counter() - t0) * 1000)
        logger.error(
            "end op=%s status=error duration=%dms error=%r %s",
            operation,
            ms,
            str(exc),
            kv,
        )
        raise
