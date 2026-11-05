import pytest

from tests.factories import make_contribution, make_member

pytestmark = pytest.mark.integration


def issue(client, member_id, due_on, principal=100_000):
    response = client.post(
        "/api/loans",
        json={
            "member_id": member_id,
            "principal": principal,
            "interest_rate_bps": 0,
            "issued_on": "2026-01-01",
            "due_on": due_on,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_ac_5_3_empty_group_shows_zeros(client):
    body = client.get("/api/dashboard").json()
    assert body["member_count"] == 0
    assert body["total_savings"] == 0
    assert body["loans_outstanding"] == 0
    assert body["par30"] == 0


def test_ac_5_1_and_5_2_totals_and_par30(client):
    late, current = make_member(client), make_member(client)
    make_contribution(client, late["id"], amount=100_000)
    make_contribution(client, current["id"], amount=100_000)
    issue(client, late["id"], due_on="2026-03-01", principal=25_000)
    issue(client, current["id"], due_on="2026-12-01", principal=75_000)

    body = client.get("/api/dashboard", params={"as_of": "2026-06-30"}).json()

    assert body["member_count"] == 2
    assert body["total_savings"] == 200_000
    assert body["loans_outstanding"] == 100_000
    assert body["par30"] == 0.25


def test_repaid_loans_leave_the_portfolio(client):
    member = make_member(client)
    make_contribution(client, member["id"], amount=100_000)
    loan = issue(client, member["id"], due_on="2026-03-01")
    client.post(
        f"/api/loans/{loan['id']}/repayments",
        json={"amount": 100_000, "paid_on": "2026-02-01", "reference": "RP-FULL"},
    )
    body = client.get("/api/dashboard", params={"as_of": "2026-06-30"}).json()
    assert body["loans_outstanding"] == 0
    assert body["par30"] == 0
