from collections import Counter
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from responder.agent import Agent
from responder.config import Settings
from responder.main import create_app


class FakeTools:
    """Models the system: the journey is broken until the right flag is turned off."""

    def __init__(self, faults=("contribution_write_failure",), fix_works=True):
        self.faults = list(faults)
        self.fix_works = fix_works
        self.disabled = []
        self.broken = True

    async def error_ratio(self):
        return 0.8

    async def p95_seconds(self):
        return 0.1

    async def recent_failures(self):
        return Counter({"ContributionWriteFault": 12}), ["trace-1"]

    async def enabled_faults(self):
        return self.faults

    async def disable_fault(self, name):
        self.disabled.append(name)
        self.faults.remove(name)
        if self.fix_works:
            self.broken = False

    async def probe(self):
        return (not self.broken), 0.05

    async def alert_is_firing(self, _name):
        return self.broken


@pytest.fixture
def settings(tmp_path):
    return Settings(
        incident_dir=str(tmp_path),
        verify_timeout_seconds=0.2,
        verify_poll_seconds=0.01,
        healthy_probes_required=2,
        probe_enabled=False,
    )


async def run(agent, alert="ContributionsFailing"):
    incident = agent.wake(alert)
    await agent._running
    return incident


async def test_fixes_a_known_fault_and_verifies_recovery(settings):
    tools = FakeTools()
    async with httpx.AsyncClient() as client:
        incident = await run(Agent(settings, client, tools))
    assert incident.status == "resolved"
    assert tools.disabled == ["contribution_write_failure"]
    assert incident.sample_trace_ids == ["trace-1"]


async def test_writes_a_report_with_the_reasoning(settings):
    async with httpx.AsyncClient() as client:
        incident = await run(Agent(settings, client, FakeTools()))
    report = (Path(settings.incident_dir) / f"{incident.id}.md").read_text()
    assert "resolved" in report
    assert "contribution_write_failure" in report
    assert "trace-1" in report


async def test_escalates_without_acting_when_the_cause_is_unknown(settings):
    tools = FakeTools(faults=())
    async with httpx.AsyncClient() as client:
        incident = await run(Agent(settings, client, tools))
    assert incident.status == "escalated"
    assert tools.disabled == []


async def test_does_not_claim_success_when_the_fix_does_not_work(settings):
    tools = FakeTools(fix_works=False)
    async with httpx.AsyncClient() as client:
        incident = await run(Agent(settings, client, tools))
    assert incident.status == "escalated"
    assert any("did not restore" in entry["message"] for entry in incident.timeline)


async def test_a_second_notification_during_an_incident_is_ignored(settings):
    async with httpx.AsyncClient() as client:
        agent = Agent(settings, client, FakeTools())
        first = agent.wake("ContributionsFailing")
        second = agent.wake("ContributionsUnavailable")
        await agent._running
    assert first is not None
    assert second is None
    assert len(agent.incidents) == 1


async def test_an_escalated_alert_stays_quiet_until_it_resolves(settings):
    async with httpx.AsyncClient() as client:
        agent = Agent(settings, client, FakeTools(faults=()))
        await run(agent)
        assert agent.wake("ContributionsFailing") is None
        agent.on_alert_resolved("ContributionsFailing")
        assert agent.wake("ContributionsFailing") is not None
        await agent._running


async def test_a_missing_evidence_source_is_recorded_and_does_not_stop_the_agent(settings):
    class NoLogs(FakeTools):
        async def recent_failures(self):
            raise httpx.ConnectError("loki down")

    async with httpx.AsyncClient() as client:
        incident = await run(Agent(settings, client, NoLogs()))
    assert incident.status == "resolved"
    assert incident.evidence["evidence_gaps"] == ["logs unavailable: ConnectError"]


async def test_a_failing_action_escalates_with_a_report(settings):
    class Locked(FakeTools):
        async def disable_fault(self, name):
            raise httpx.ConnectError("api down")

    async with httpx.AsyncClient() as client:
        incident = await run(Agent(settings, client, Locked()))
    assert incident.status == "escalated"
    assert (Path(settings.incident_dir) / f"{incident.id}.md").exists()


WEBHOOK = {"alerts": [{"status": "firing", "labels": {"alertname": "ContributionsFailing"}}]}
AUTH = {"Authorization": "Bearer local-responder-token"}


def test_webhook_rejects_a_missing_or_wrong_token(settings):
    with TestClient(create_app(settings)) as client:
        assert client.post("/alerts", json=WEBHOOK).status_code == 401
        wrong = {"Authorization": "Bearer nope"}
        assert client.post("/alerts", json=WEBHOOK, headers=wrong).status_code == 401
        assert client.get("/incidents").json() == []


def test_webhook_wakes_the_agent(settings):
    with TestClient(create_app(settings)) as client:
        response = client.post("/alerts", json=WEBHOOK, headers=AUTH)
        assert response.status_code == 200
        assert len(response.json()["started"]) == 1
        assert client.get("/incidents").json()[0]["alert_name"] == "ContributionsFailing"


def test_resolved_notifications_do_not_start_an_incident(settings):
    body = {"alerts": [{"status": "resolved", "labels": {"alertname": "ContributionsFailing"}}]}
    with TestClient(create_app(settings)) as client:
        assert client.post("/alerts", json=body, headers=AUTH).json() == {"started": []}


def test_metrics_expose_the_probe_result(settings):
    with TestClient(create_app(settings)) as client:
        assert "chama_probe_success 1" in client.get("/metrics").text


