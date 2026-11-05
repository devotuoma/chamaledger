import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.faults import WRITE_FAILURE, WRITE_LATENCY
from app.main import app
from tests.factories import make_member

pytestmark = pytest.mark.integration

TOKEN = {"X-Ops-Token": "secret"}


def use_settings(monkeypatch, **values):
    settings = Settings(**values)
    monkeypatch.setattr("app.routers.ops.get_settings", lambda: settings)
    monkeypatch.setattr("app.faults.get_settings", lambda: settings)


@pytest.fixture
def chaos(monkeypatch):
    use_settings(monkeypatch, ops_token="secret", chaos_enabled=True)
    monkeypatch.setattr("app.faults.INJECTED_DELAY_SECONDS", 0)


@pytest.fixture
def lenient_client():
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


def contribute(client, member_id):
    return client.post(
        "/api/contributions",
        json={"member_id": member_id, "amount": 1, "paid_on": "2026-01-01", "reference": "F-1"},
    )


def test_ops_api_does_not_exist_without_a_configured_token(client, monkeypatch):
    use_settings(monkeypatch, ops_token="")
    assert client.get("/api/ops/flags", headers=TOKEN).status_code == 404


def test_a_wrong_token_is_rejected(client, chaos):
    assert client.get("/api/ops/flags", headers={"X-Ops-Token": "nope"}).status_code == 401
    assert client.get("/api/ops/flags").status_code == 401


def test_flags_start_off_and_can_be_changed(client, chaos):
    assert client.get("/api/ops/flags", headers=TOKEN).json() == {
        WRITE_FAILURE: False,
        WRITE_LATENCY: False,
    }
    response = client.put(f"/api/ops/flags/{WRITE_FAILURE}", json={"enabled": True}, headers=TOKEN)
    assert response.json()[WRITE_FAILURE] is True


def test_unknown_flag_is_not_found(client, chaos):
    response = client.put("/api/ops/flags/whatever", json={"enabled": True}, headers=TOKEN)
    assert response.status_code == 404


def test_write_failure_flag_breaks_the_journey_until_turned_off(client, lenient_client, chaos):
    member = make_member(client)
    client.put(f"/api/ops/flags/{WRITE_FAILURE}", json={"enabled": True}, headers=TOKEN)
    assert contribute(lenient_client, member["id"]).status_code == 500
    client.put(f"/api/ops/flags/{WRITE_FAILURE}", json={"enabled": False}, headers=TOKEN)
    assert contribute(lenient_client, member["id"]).status_code == 201


def test_flags_have_no_effect_when_chaos_is_disabled(client, monkeypatch):
    use_settings(monkeypatch, ops_token="secret", chaos_enabled=False)
    member = make_member(client)
    client.put(f"/api/ops/flags/{WRITE_FAILURE}", json={"enabled": True}, headers=TOKEN)
    assert contribute(client, member["id"]).status_code == 201


def test_probe_leaves_no_data_behind(client, chaos):
    for _ in range(2):  # Twice, because a leftover row would make the second run conflict.
        assert client.post("/api/ops/probe", headers=TOKEN).status_code == 200
    assert client.get("/api/members").json() == []
    assert client.get("/api/contributions").json() == []


def test_probe_fails_when_the_journey_is_broken(client, lenient_client, chaos):
    client.put(f"/api/ops/flags/{WRITE_FAILURE}", json={"enabled": True}, headers=TOKEN)
    assert lenient_client.post("/api/ops/probe", headers=TOKEN).status_code == 500
    assert client.get("/api/members").json() == []
