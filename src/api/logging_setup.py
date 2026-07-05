"""Structured-logging setup for the GMNAP API (R46 split from server.py).

GMNAP_LOG_FORMAT: text (default) | json.  GMNAP_LOG_LEVEL passes through.
Both read at app-factory time; restart workers to change them.
"""

import logging
import os
from typing import Any, Dict


class _JSONLogFormatter(logging.Formatter):
    """Minimal JSON formatter — no third-party dep needed."""

    def format(self, record: logging.LogRecord) -> str:
        import json as _json

        payload: Dict[str, Any] = {
            "ts": self.formatTime(record, datefmt="%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        # Pass through any extra fields the caller attached with
        # logger.info("msg", extra={"key": "value"}).
        for k, v in record.__dict__.items():
            if k not in {
                "args",
                "asctime",
                "created",
                "exc_info",
                "exc_text",
                "filename",
                "funcName",
                "levelname",
                "levelno",
                "lineno",
                "message",
                "module",
                "msecs",
                "msg",
                "name",
                "pathname",
                "process",
                "processName",
                "relativeCreated",
                "stack_info",
                "thread",
                "threadName",
                "taskName",
            }:
                payload[k] = v
        return _json.dumps(payload, default=str)


def _configure_logging() -> None:
    """Idempotent — safe to call from create_app and from CLI."""
    level = os.getenv("GMNAP_LOG_LEVEL", "INFO").upper()
    fmt = os.getenv("GMNAP_LOG_FORMAT", "text").lower()
    root = logging.getLogger()
    # Don't re-wire if we already installed a handler; respects
    # operator pre-config (uvicorn --log-config etc).
    if any(getattr(h, "_gmnap_managed", False) for h in root.handlers):
        return
    root.setLevel(level)
    handler = logging.StreamHandler()
    handler._gmnap_managed = True  # type: ignore[attr-defined]
    if fmt == "json":
        handler.setFormatter(_JSONLogFormatter())
    else:
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
        )
    root.addHandler(handler)
