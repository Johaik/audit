import pytest
from httpx import AsyncClient
import asyncio

@pytest.mark.anyio
async def test_tenant_isolation_idempotency(client: AsyncClient, auth_headers):
    """
    Test that the same idempotency key can be used across different tenants
    without conflict.
    """
    payload = {
        "idempotency_key": "shared-key-1",
        "occurred_at": "2025-12-19T10:11:12Z",
        "type": "shared.event",
        "actor": { "kind": "system", "id": "sys" },
        "entities": [],
        "payload": { "val": 100 }
    }

    # Tenant A
    headers_a = auth_headers("tenant-A")
    resp_a = await client.post("/v1/events", json=payload, headers=headers_a)
    assert resp_a.status_code == 201
    event_a_id = resp_a.json()["event_id"]

    # Tenant B (same payload, same key)
    headers_b = auth_headers("tenant-B")
    resp_b = await client.post("/v1/events", json=payload, headers=headers_b)
    assert resp_b.status_code == 201
    event_b_id = resp_b.json()["event_id"]

    # Ensure events are distinct
    assert event_a_id != event_b_id

@pytest.mark.anyio
async def test_tenant_data_isolation(client: AsyncClient, auth_headers):
    """
    Test that queries for one tenant do not return data for another.
    """
    payload_a = {
        "idempotency_key": "iso-req-a",
        "occurred_at": "2025-12-20T10:00:00Z",
        "type": "event.a",
        "actor": { "kind": "user", "id": "u1" },
        "entities": [{ "kind": "thing", "id": "t1" }],
        "payload": {}
    }
    
    payload_b = {
        "idempotency_key": "iso-req-b",
        "occurred_at": "2025-12-20T10:00:00Z",
        "type": "event.b",
        "actor": { "kind": "user", "id": "u2" },
        "entities": [{ "kind": "thing", "id": "t1" }], # Same entity ID, different tenant
        "payload": {}
    }

    # Create events
    await client.post("/v1/events", json=payload_a, headers=auth_headers("tenant-A"))
    await client.post("/v1/events", json=payload_b, headers=auth_headers("tenant-B"))

    # Query Timeline for Tenant A
    resp = await client.get("/v1/timeline?entity=thing:t1", headers=auth_headers("tenant-A"))
    data = resp.json()
    assert len(data["events"]) == 1
    assert data["events"][0]["type"] == "event.a"

    # Query Timeline for Tenant B
    resp = await client.get("/v1/timeline?entity=thing:t1", headers=auth_headers("tenant-B"))
    data = resp.json()
    assert len(data["events"]) == 1
    assert data["events"][0]["type"] == "event.b"

@pytest.mark.anyio
async def test_concurrent_idempotency_race(client: AsyncClient, auth_headers):
    """
    Simulate concurrent requests with the same idempotency key for the same tenant.
    Only one should return 201, the other 200 (or both 200/201 depending on timing, 
    but importantly NO 500s or constraint errors surfaced to user).
    """
    payload = {
        "idempotency_key": "race-key-1",
        "occurred_at": "2025-12-21T12:00:00Z",
        "type": "race.event",
        "actor": { "kind": "bot", "id": "b1" },
        "entities": [],
        "payload": { "race": True }
    }
    headers = auth_headers("tenant-race")

    async def make_request():
        return await client.post("/v1/events", json=payload, headers=headers)

    # Launch 5 concurrent requests
    responses = await asyncio.gather(*[make_request() for _ in range(5)])
    
    status_codes = [r.status_code for r in responses]
    
    # We expect at least one 201 (creation) and the rest 200 (idempotent return)
    # OR all 200 if somehow pre-seeded (not here)
    # OR multiple 201s if the race isn't caught (bad) - BUT our DB constraint prevents this.
    # The DB constraint ensures only one INSERT succeeds. The others hit the IntegrityError catch block.
    
    num_201 = status_codes.count(201)
    num_200 = status_codes.count(200)
    
    assert num_201 == 1
    assert num_200 == 4
    
    # Verify all returned the same event ID
    event_ids = {r.json()["event_id"] for r in responses}
    assert len(event_ids) == 1

@pytest.mark.anyio
async def test_idempotency_hash_mismatch_details(client: AsyncClient, auth_headers):
    """
    Verify exact behavior when hash mismatches on an existing idempotency key.
    """
    headers = auth_headers("tenant-hash")
    key = "hash-key-1"
    
    # Initial Event
    payload1 = {
        "idempotency_key": key,
        "occurred_at": "2025-12-22T10:00:00Z",
        "type": "original",
        "actor": { "kind": "user", "id": "u1" },
        "entities": [],
        "payload": { "v": 1 }
    }
    await client.post("/v1/events", json=payload1, headers=headers)
    
    # Mismatch Event (different actor)
    payload2 = payload1.copy()
    payload2["actor"] = { "kind": "user", "id": "u2" } 
    
    resp = await client.post("/v1/events", json=payload2, headers=headers)
    assert resp.status_code == 409
    assert "hash mismatch" in resp.json()["detail"]

