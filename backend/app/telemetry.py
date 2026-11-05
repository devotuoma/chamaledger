import logging
import time

from fastapi import FastAPI, Request, Response
from opentelemetry import metrics, trace
from opentelemetry.trace import Status, StatusCode

from app.config import Settings
from app.db import engine
from app.logs import current_trace_ids, log_event

API_PREFIX = "/api"

# Requests on these routes make up a user journey that has an SLO.
JOURNEYS = {
    ("POST", "/api/contributions"): "record_contribution",
}
DURATION_BUCKETS = [0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0]

_meter = metrics.get_meter("chamaledger")
_tracer = trace.get_tracer("chamaledger")
_journey_requests = _meter.create_counter(
    "chama.journey.requests", description="Journey requests by outcome"
)
_journey_duration = _meter.create_histogram(
    "chama.journey.duration",
    unit="s",
    description="Journey duration",
    explicit_bucket_boundaries_advisory=DURATION_BUCKETS,
)


def classify(status: int) -> str:
    """Failures the user caused (4xx) are not failures of the service."""
    if status >= 500:
        return "error"
    if status >= 400:
        return "rejected"
    return "success"


def _route_of(request: Request) -> str:
    """The route template, never the raw path, so that IDs cannot explode log cardinality."""
    route = request.scope.get("route")
    if route is None:
        return "unmatched"
    # FastAPI reports the path relative to the prefix given to include_router.
    return f"{API_PREFIX}{route.path}"


def _observe(request: Request, status: int, started: float, error: Exception | None) -> None:
    route = _route_of(request)
    duration = time.perf_counter() - started
    outcome = classify(status)
    journey = JOURNEYS.get((request.method, route))
    if journey:
        attributes = {"journey": journey, "outcome": outcome}
        _journey_requests.add(1, attributes)
        _journey_duration.record(duration, attributes)
    log_event(
        "http_request",
        level=logging.ERROR if status >= 500 else logging.INFO,
        method=request.method,
        route=route,
        status=status,
        duration_ms=round(duration * 1000, 1),
        journey=journey,
        outcome=outcome,
        error_type=type(error).__name__ if error else None,
    )


def add_observability_middleware(app: FastAPI) -> None:
    @app.middleware("http")
    async def observe(request: Request, call_next) -> Response:
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception as error:
            _observe(request, 500, started, error)
            raise
        _observe(request, response.status_code, started, None)
        trace_id, _ = current_trace_ids()
        if trace_id:
            response.headers["X-Trace-Id"] = trace_id
        return response


def journey_span(name: str):
    """A span around the business step, with nothing about the customer in it."""
    return _tracer.start_as_current_span(f"journey.{name}")


def mark_span_failed(error: Exception) -> None:
    trace.get_current_span().set_status(Status(StatusCode.ERROR, type(error).__name__))


def configure_telemetry(app: FastAPI, settings: Settings, log_handler: logging.Handler) -> None:
    """Connects the SDK to the collector. Without this call, the API above is a no-op."""
    if not settings.otel_enabled:
        return

    from opentelemetry._logs import set_logger_provider
    from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
    from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.instrumentation.logging.handler import LoggingHandler
    from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
    from opentelemetry.sdk._logs import LoggerProvider
    from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    resource = Resource.create(
        {
            "service.name": "chamaledger-api",
            "service.version": settings.service_version,
            "deployment.environment": settings.environment,
        }
    )
    endpoint = settings.otel_endpoint.rstrip("/")

    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter(endpoint=f"{endpoint}/v1/traces"))
    )
    trace.set_tracer_provider(tracer_provider)

    metrics.set_meter_provider(
        MeterProvider(
            resource=resource,
            metric_readers=[
                PeriodicExportingMetricReader(
                    OTLPMetricExporter(endpoint=f"{endpoint}/v1/metrics"),
                    export_interval_millis=5000,
                )
            ],
        )
    )

    logger_provider = LoggerProvider(resource=resource)
    logger_provider.add_log_record_processor(
        BatchLogRecordProcessor(OTLPLogExporter(endpoint=f"{endpoint}/v1/logs"))
    )
    set_logger_provider(logger_provider)
    otel_handler = LoggingHandler(logger_provider=logger_provider)
    for log_filter in log_handler.filters:
        otel_handler.addFilter(log_filter)
    logging.getLogger().addHandler(otel_handler)
    # The exporter's own failures must not be exported, or they feed back into themselves.
    exporter_logger = logging.getLogger("opentelemetry")
    exporter_logger.propagate = False
    exporter_logger.addHandler(log_handler)

    SQLAlchemyInstrumentor().instrument(engine=engine)
    FastAPIInstrumentor.instrument_app(app, excluded_urls="api/health")
