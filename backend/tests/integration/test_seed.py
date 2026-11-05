import pytest

from app.seed import seed

pytestmark = pytest.mark.integration


def test_seed_fills_an_empty_database_with_a_late_loan(client):
    assert seed() is True
    body = client.get("/api/dashboard").json()
    assert body["member_count"] == 4
    assert body["par30"] > 0


def test_seed_never_touches_existing_data(client):
    assert seed() is True
    before = client.get("/api/dashboard").json()
    assert seed() is False
    assert client.get("/api/dashboard").json() == before
