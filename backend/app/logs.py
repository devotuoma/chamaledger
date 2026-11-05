"""Structured JSON logs. Fields are allowlisted, so customer data cannot be logged by accident."""

import json
import logging
import sys
from datetime import datetime, timezone

from opentelemetry import trace

logger = logging.getLogger("chamaledger")

ALLOWED_FIELDS = frozenset(
    {"event", "method", "route", "status", "duration_ms", "journey", "outcome", "error_type"}
)


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
            "timestamp": datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
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
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(level)
    # Request logging is done by our middleware, which knows the route and the trace.
    logging.getLogger("uvicorn.access").disabled = True
    return handler
