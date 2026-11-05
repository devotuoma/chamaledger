import json
import logging

import pytest
from fastapi.testclient import TestClient
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider

from app.logs import JsonFormatter
from app.main import app
from app.telemetry import classify
from tests.factories import make_member

pytestmark = pytest.mark.integration


class Capture(logging.Handler):
    def __init__(self):
        super().__init__()
        self.setFormatter(JsonFormatter())
        self.lines = []

    def emit(self, record):
        self.lines.append(json.loads(self.format(record)))


@pytest.fixture
def logs():
    handler = Capture()
    root = logging.getLogger()
    root.addHandler(handler)
    yield handler.lines
    root.removeHandler(handler)


@pytest.mark.parametrize(
    ("status", "outcome"), [(200, "success"), (201, "success"), (409, "rejected"), (500, "error")]
)
def test_only_server_failures_count_against_the_service(status, outcome):
    assert classify(status) == outcome


def test_request_log_names_the_route_template_and_journey(client, logs):
    member = make_member(client)
    client.post(
        "/api/contributions",
        json={"member_id": member["id"], "amount": 1, "paid_on": "2026-01-01", "reference": "T-1"},
    )
    line = [entry for entry in logs if entry.get("route") == "/api/contributions"][-1]
    assert line["event"] == "http_request"
    assert line["journey"] == "record_contribution"
    assert line["outcome"] == "success"
    assert line["status"] == 201


def test_log_lines_carry_the_active_trace_id(logs):
    tracer = TracerProvider().get_tracer("test")
    logger = logging.getLogger("chamaledger")
    with tracer.start_as_current_span("request") as span:
        logger.info("inside")
        expected = format(span.get_span_context().trace_id, "032x")
    assert trace.get_current_span().get_span_context().is_valid is False
    assert logs[-1]["trace_id"] == expected


def test_unhandled_errors_are_logged_as_error_outcomes(logs, monkeypatch):
    def boom(*_args, **_kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr("app.services.contributions.record_contribution", boom)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(
            "/api/contributions",
            json={"member_id": 1, "amount": 1, "paid_on": "2026-01-01", "reference": "T-2"},
        )
    assert response.status_code == 500
    line = [entry for entry in logs if entry.get("route") == "/api/contributions"][-1]
    assert line["outcome"] == "error"
    assert line["error_type"] == "RuntimeError"
