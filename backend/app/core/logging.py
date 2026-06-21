import logging
import sys
from typing import Any

import structlog

from app.config import get_settings


def setup_structlog_logging() -> None:
    """Configure structured logging for the application.

    Routes standard library logging through structlog for JSON formatting.
    """
    settings = get_settings()

    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    structlog.configure(
        processors=shared_processors
        + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.processors.JSONRenderer(),
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    root_logger.setLevel(logging.INFO if not settings.debug else logging.DEBUG)

    # Route uvicorn logs through the root logger to use JSON format
    for logger_name in ["uvicorn", "uvicorn.error", "uvicorn.access", "fastapi"]:
        logger = logging.getLogger(logger_name)
        logger.handlers = []
        logger.propagate = True

# --- Structured JSON Logging Factory ---
import json
import traceback
from datetime import datetime

try:
    import contextvars
    # Use contextvars to maintain trace IDs across async boundaries
    request_id_ctx = contextvars.ContextVar("request_id", default="-")
except ImportError:
    request_id_ctx = None  # type: ignore[assignment]

class JSONLogFormatter(logging.Formatter):
    """
    A comprehensive JSON formatter for centralized logging systems (e.g., ELK, Datadog).
    Injects distributed tracing correlation IDs and environment metadata into every log line.
    """
    def __init__(self, env: str = "production", service_name: str = "envforage-api"):
        super().__init__()
        self.env = env
        self.service_name = service_name

    def format(self, record: logging.LogRecord) -> str:
        log_obj: dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "module": record.module,
            "line": record.lineno,
            "env": self.env,
            "service": self.service_name
        }

        # Inject Trace ID from contextvars if available
        if request_id_ctx:
            log_obj["trace_id"] = request_id_ctx.get()

        # Handle exceptions deeply
        if record.exc_info and record.exc_info[0] and record.exc_info[1]:
            log_obj["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": "".join(traceback.format_exception(*record.exc_info))
            }

        # Include arbitrary extra attributes passed via `logger.info("...", extra={"user_id": 123})`
        for key, val in record.__dict__.items():
            if key not in logging.LogRecord("", 0, "", 0, "", (), None).__dict__:
                log_obj[key] = val

        try:
            return json.dumps(log_obj, default=str)
        except Exception as e:
            # Fallback if json encoding fails for some weird object
            return json.dumps({"error": f"JSON Encoding failed: {str(e)}", "message": str(record.msg)})

def setup_logging(env: str = "production", level: int = logging.INFO):
    """
    Replaces the root logger handlers with the JSONLogFormatter.
    This ensures third-party libraries (e.g., uvicorn, sqlalchemy) also
    output structured JSON logs.
    """
    root_logger = logging.getLogger()

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    root_logger.setLevel(level)

    console_handler = logging.StreamHandler()

    if env == "development":
        # In dev, we might prefer human-readable color logs
        formatter = logging.Formatter("[%(asctime)s] %(levelname)s [%(name)s] %(message)s")
    else:
        # In prod, JSON all the way
        formatter = JSONLogFormatter(env=env)

    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    logging.getLogger("uvicorn.access").setLevel(logging.WARNING) # Reduce noise

    return root_logger
