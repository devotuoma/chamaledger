from itertools import count

_phones = count(256700000001)
_references = count(1)


def make_member(client, full_name: str = "Akinyi Test") -> dict:
    response = client.post(
        "/api/members", json={"full_name": full_name, "phone": f"+{next(_phones)}"}
    )
    assert response.status_code == 201, response.text
    return response.json()


def make_contribution(client, member_id: int, amount: int = 50_000, **overrides) -> dict:
    payload = {
        "member_id": member_id,
        "amount": amount,
        "paid_on": "2026-01-15",
        "reference": f"MM-{next(_references)}",
        **overrides,
    }
    response = client.post("/api/contributions", json=payload)
    assert response.status_code == 201, response.text
    return response.json()
