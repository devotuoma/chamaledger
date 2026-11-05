from concurrent.futures import ThreadPoolExecutor

import pytest

from tests.factories import make_contribution, make_member

pytestmark = pytest.mark.integration


def payload(member_id, **overrides):
    return {
        "member_id": member_id,
        "amount": 20_000,
        "paid_on": "2026-02-01",
        "reference": "MM-REPLAY",
        **overrides,
    }


def test_ac_2_1_contribution_adds_to_member_savings(client):
    member = make_member(client)
    make_contribution(client, member["id"], amount=30_000)
    make_contribution(client, member["id"], amount=12_000)
    assert client.get("/api/members").json()[0]["savings"] == 42_000


def test_ac_2_2_replay_returns_the_original_and_creates_nothing(client):
    member = make_member(client)
    first = client.post("/api/contributions", json=payload(member["id"]))
    second = client.post("/api/contributions", json=payload(member["id"]))
    assert (first.status_code, second.status_code) == (201, 200)
    assert second.json()["id"] == first.json()["id"]
    assert len(client.get("/api/contributions").json()) == 1


def test_ac_2_3_reused_reference_with_different_data_is_a_conflict(client):
    member = make_member(client)
    client.post("/api/contributions", json=payload(member["id"]))
    response = client.post("/api/contributions", json=payload(member["id"], amount=99))
    assert response.status_code == 409


def test_ac_2_4_inactive_member_is_a_conflict(client):
    member = make_member(client)
    client.post(f"/api/members/{member['id']}/deactivate")
    assert client.post("/api/contributions", json=payload(member["id"])).status_code == 409


def test_ac_2_4_unknown_member_is_not_found(client):
    assert client.post("/api/contributions", json=payload(4242)).status_code == 404


@pytest.mark.parametrize("amount", [0, -1])
def test_ac_2_5_non_positive_amount_is_rejected(client, amount):
    member = make_member(client)
    response = client.post("/api/contributions", json=payload(member["id"], amount=amount))
    assert response.status_code == 422


def test_filter_contributions_by_member(client):
    one, two = make_member(client), make_member(client)
    make_contribution(client, one["id"])
    make_contribution(client, two["id"])
    listed = client.get("/api/contributions", params={"member_id": one["id"]}).json()
    assert [c["member_id"] for c in listed] == [one["id"]]


def test_concurrent_retries_record_the_payment_once(client):
    member = make_member(client)
    with ThreadPoolExecutor(max_workers=4) as pool:
        responses = list(
            pool.map(
                lambda _: client.post("/api/contributions", json=payload(member["id"])), range(8)
            )
        )
    assert {r.status_code for r in responses} <= {200, 201}
    assert len(client.get("/api/contributions").json()) == 1
