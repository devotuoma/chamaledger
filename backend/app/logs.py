"""Structured JSON logs. Fields are allowlisted, so customer data cannot be logged by accident."""

import json
import logging
import re
import sys
from datetime import UTC, datetime

from opentelemetry import trace

logger = logging.getLogger("chamaledger")

ALLOWED_FIELDS = frozenset(
    {"event", "method", "route", "status", "duration_ms", "journey", "outcome", "error_type"}
)


PHONE_PATTERN = re.compile(r"\+[1-9]\d{7,14}")
REDACTED = "[REDACTED]"


class RedactingFilter(logging.Filter):
    """Second line of defence for messages from libraries, which skip the allowlist."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = PHONE_PATTERN.sub(REDACTED, record.getMessage())
        record.args = None
        if record.exc_info:
            # Keep the exception type but drop a message that may quote customer data.
            exc_type = record.exc_info[0]
            record.msg = f"{record.msg} ({exc_type.__name__ if exc_type else 'error'})"
            record.exc_info = None
            record.exc_text = None
        return True


def current_trace_ids() -> tuple[str | None, str | None]:
    context = trace.get_current_span().get_span_context()
    if not context.is_valid:
        return None, None
    return format(context.trace_id, "032x"), format(context.span_id, "016x")


def log_event(event: str, level: int = logging.INFO, **fields: object) -> None:
    safe = {key: value for key, value in fields.items() if key in ALLOWED_FIELDS}
    logger.log(level, event, extra={"event": event, **safe})


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        trace_id, span_id = current_trace_ids()
        entry = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "trace_id": trace_id,
            "span_id": span_id,
        }
        entry.update(
            {key: getattr(record, key) for key in ALLOWED_FIELDS if hasattr(record, key)}
        )
        return json.dumps(entry, default=str)


def configure_logging(level: str = "INFO") -> logging.Handler:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    handler.addFilter(RedactingFilter())
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(level)
    # Request logging is done by our middleware, which knows the route and the trace.
    logging.getLogger("uvicorn.access").disabled = True
    return handler
