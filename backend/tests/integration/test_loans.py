import pytest

from tests.factories import make_contribution, make_member

pytestmark = pytest.mark.integration


@pytest.fixture
def saver(client):
    member = make_member(client)
    make_contribution(client, member["id"], amount=100_000)
    return member


def loan_payload(member_id, principal=100_000, **overrides):
    return {
        "member_id": member_id,
        "principal": principal,
        "interest_rate_bps": 1000,
        "issued_on": "2026-01-01",
        "due_on": "2026-04-01",
        **overrides,
    }


def repay(client, loan_id, amount, reference="RP-1"):
    return client.post(
        f"/api/loans/{loan_id}/repayments",
        json={"amount": amount, "paid_on": "2026-02-01", "reference": reference},
    )


def test_ac_3_1_principal_up_to_three_times_savings_is_allowed(client, saver):
    response = client.post("/api/loans", json=loan_payload(saver["id"], principal=300_000))
    assert response.status_code == 201
    assert response.json()["total_due"] == 330_000


def test_ac_3_1_principal_above_three_times_savings_is_rejected(client, saver):
    response = client.post("/api/loans", json=loan_payload(saver["id"], principal=300_001))
    assert response.status_code == 409


def test_ac_3_2_only_one_open_loan_per_member(client, saver):
    assert client.post("/api/loans", json=loan_payload(saver["id"])).status_code == 201
    assert client.post("/api/loans", json=loan_payload(saver["id"])).status_code == 409


def test_due_date_must_follow_the_issue_date(client, saver):
    response = client.post("/api/loans", json=loan_payload(saver["id"], due_on="2025-12-31"))
    assert response.status_code == 422


def test_ac_4_1_repayment_above_the_balance_is_rejected(client, saver):
    loan = client.post("/api/loans", json=loan_payload(saver["id"])).json()
    assert repay(client, loan["id"], 110_001).status_code == 409


def test_ac_4_2_full_repayment_closes_the_loan_and_allows_another(client, saver):
    loan = client.post("/api/loans", json=loan_payload(saver["id"])).json()
    assert repay(client, loan["id"], 10_000, "RP-A").json()["outstanding"] == 100_000
    closed = repay(client, loan["id"], 100_000, "RP-B").json()
    assert closed["outstanding"] == 0
    assert closed["closed_on"] == "2026-02-01"
    assert client.post("/api/loans", json=loan_payload(saver["id"])).status_code == 201


def test_ac_4_3_replayed_repayment_counts_once(client, saver):
    loan = client.post("/api/loans", json=loan_payload(saver["id"])).json()
    first, second = repay(client, loan["id"], 10_000), repay(client, loan["id"], 10_000)
    assert (first.status_code, second.status_code) == (201, 200)
    assert second.json()["outstanding"] == 100_000


def test_ac_4_3_reused_reference_with_a_different_amount_is_a_conflict(client, saver):
    loan = client.post("/api/loans", json=loan_payload(saver["id"])).json()
    repay(client, loan["id"], 10_000)
    assert repay(client, loan["id"], 5_000).status_code == 409


def test_repaying_an_unknown_loan_is_not_found(client):
    assert repay(client, 9999, 100).status_code == 404
