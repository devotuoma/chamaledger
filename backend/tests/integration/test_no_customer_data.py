"""AC-6.2: names, phone numbers and notes never reach telemetry."""

import json
import logging

import pytest
from fastapi.testclient import TestClient
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from app.db import engine
from app.logs import JsonFormatter, RedactingFilter
from app.main import create_app

pytestmark = pytest.mark.integration

NAME = "Zawadi Secretname"
PHONE = "+256799912345"
NOTE = "school fees secret note"
SECRETS = (NAME, PHONE, NOTE, "Secretname")


class Capture(logging.Handler):
    def __init__(self):
        super().__init__()
        self.setFormatter(JsonFormatter())
        self.addFilter(RedactingFilter())
        self.lines = []

    def emit(self, record):
        self.lines.append(self.format(record))


@pytest.fixture
def telemetry():
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    SQLAlchemyInstrumentor().instrument(engine=engine, tracer_provider=provider)
    capture = Capture()
    logging.getLogger().addHandler(capture)
    app = create_app()
    logging.getLogger().addHandler(capture)
    FastAPIInstrumentor.instrument_app(app, tracer_provider=provider)
    try:
        yield app, exporter, capture
    finally:
        logging.getLogger().removeHandler(capture)
        FastAPIInstrumentor.uninstrument_app(app)
        SQLAlchemyInstrumentor().uninstrument()


def walk_the_journey(client):
    member = client.post("/api/members", json={"full_name": NAME, "phone": PHONE})
    assert member.status_code == 201
    member_id = member.json()["id"]
    payment = {
        "member_id": member_id,
        "amount": 500,
        "paid_on": "2026-01-01",
        "reference": "PII-1",
        "note": NOTE,
    }
    assert client.post("/api/contributions", json=payment).status_code == 201
    # The failure paths are where values most often leak.
    assert client.post("/api/members", json={"full_name": NAME, "phone": PHONE}).status_code == 409
    assert client.post("/api/members", json={"full_name": NAME, "phone": "bad"}).status_code == 422
    assert client.get("/api/members").status_code == 200


def test_ac_6_2_spans_and_logs_hold_no_customer_data(telemetry):
    app, exporter, capture = telemetry
    with TestClient(app) as client:
        walk_the_journey(client)

    spans = exporter.get_finished_spans()
    assert any(span.name.startswith("POST") for span in spans), "instrumentation did not run"
    assert capture.lines, "logging did not run"
    dumped = "\n".join(span.to_json() for span in spans) + "\n" + "\n".join(capture.lines)
    for secret in SECRETS:
        assert secret not in dumped


def test_log_event_drops_fields_outside_the_allowlist(caplog):
    from app.logs import log_event

    with caplog.at_level(logging.INFO, logger="chamaledger"):
        log_event("x", route="/ok", phone=PHONE, full_name=NAME)
    record = caplog.records[-1]
    assert record.route == "/ok"
    assert not hasattr(record, "phone")
    assert not hasattr(record, "full_name")


def test_library_messages_and_exceptions_are_scrubbed():
    capture = Capture()
    logger = logging.getLogger("some.library")
    logger.addHandler(capture)
    logger.propagate = False
    try:
        logger.warning("failed for %s", PHONE)
        try:
            raise ValueError(f"duplicate key {PHONE}")
        except ValueError:
            logger.exception("insert failed")
    finally:
        logger.removeHandler(capture)
        logger.propagate = True
    assert PHONE not in "\n".join(capture.lines)
    assert "ValueError" in json.loads(capture.lines[-1])["message"]


def test_a_real_database_error_message_hides_the_values(client):
    from sqlalchemy import insert
    from sqlalchemy.exc import IntegrityError

    from app.models import Member

    row = {"full_name": NAME, "phone": PHONE, "active": True}
    with engine.begin() as connection:
        connection.execute(insert(Member).values(**row))
    with pytest.raises(IntegrityError) as error, engine.begin() as connection:
        connection.execute(insert(Member).values(**row))
    assert PHONE not in str(error.value)
    assert trace.get_current_span().get_span_context().is_valid is False
