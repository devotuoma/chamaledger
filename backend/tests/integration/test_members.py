import pytest

from tests.factories import make_member

pytestmark = pytest.mark.integration


def test_ac_1_1_add_and_list_a_member(client):
    member = make_member(client, "Wanjiru Test")
    listed = client.get("/api/members").json()
    assert [m["id"] for m in listed] == [member["id"]]
    assert listed[0]["savings"] == 0
    assert listed[0]["active"] is True


@pytest.mark.parametrize("phone", ["0700000001", "+0700000001", "+2567", "abc"])
def test_ac_1_2_reject_a_phone_that_is_not_e164(client, phone):
    response = client.post("/api/members", json={"full_name": "Bad Phone", "phone": phone})
    assert response.status_code == 422


def test_ac_1_3_duplicate_phone_is_a_conflict(client):
    payload = {"full_name": "First Person", "phone": "+256711111111"}
    assert client.post("/api/members", json=payload).status_code == 201
    assert client.post("/api/members", json=payload).status_code == 409


def test_ac_1_4_deactivate_keeps_the_member_on_record(client):
    member = make_member(client)
    response = client.post(f"/api/members/{member['id']}/deactivate")
    assert response.status_code == 200
    assert response.json()["active"] is False
    assert len(client.get("/api/members").json()) == 1


def test_deactivating_an_unknown_member_is_not_found(client):
    assert client.post("/api/members/9999/deactivate").status_code == 404
