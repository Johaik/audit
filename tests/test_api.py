import pytest
from httpx import AsyncClient

@pytest.mark.anyio
async def test_health_check(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

@pytest.mark.anyio
async def test_create_event(client: AsyncClient):
    payload = {
        "idempotency_key": "test-req-1",
        "occurred_at": "2025-12-19T10:11:12Z",
        "type": "user.created",
        "actor": { "kind": "admin", "id": "admin-1" },
        "entities": [
            { "kind": "user", "id": "u-100" }
        ],
        "payload": { "email": "test@example.com" }
    }
    headers = {"X-Tenant-ID": "tenant-A"}
    
    response = await client.post("/v1/events", json=payload, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert data["type"] == "user.created"
    assert data["tenant_id"] == "tenant-A"

@pytest.mark.anyio
async def test_idempotency_same_payload(client: AsyncClient):
    payload = {
        "idempotency_key": "test-req-2",
        "occurred_at": "2025-12-19T10:11:12Z",
        "type": "invoice.paid",
        "actor": { "kind": "system", "id": "sys" },
        "entities": [],
        "payload": { "amount": 50 }
    }
    headers = {"X-Tenant-ID": "tenant-A"}

    # First request
    resp1 = await client.post("/v1/events", json=payload, headers=headers)
    assert resp1.status_code == 201

    # Second request (duplicate)
    resp2 = await client.post("/v1/events", json=payload, headers=headers)
    assert resp2.status_code == 200
    assert resp2.json()["event_id"] == resp1.json()["event_id"]

@pytest.mark.anyio
async def test_idempotency_conflict(client: AsyncClient):
    headers = {"X-Tenant-ID": "tenant-A"}
    key = "test-req-3"
    
    payload1 = {
        "idempotency_key": key,
        "occurred_at": "2025-12-19T10:00:00Z",
        "type": "type-A",
        "actor": { "kind": "user", "id": "u1" },
        "entities": [],
        "payload": { "val": 1 }
    }
    
    payload2 = payload1.copy()
    payload2["type"] = "type-B" # Changed field
    
    await client.post("/v1/events", json=payload1, headers=headers)
    
    response = await client.post("/v1/events", json=payload2, headers=headers)
    assert response.status_code == 409

@pytest.mark.anyio
async def test_get_timeline(client: AsyncClient):
    headers = {"X-Tenant-ID": "tenant-A"}
    
    # Create event for timeline
    event_payload = {
        "idempotency_key": "timeline-req-1",
        "occurred_at": "2025-01-01T12:00:00Z",
        "type": "doc.signed",
        "actor": { "kind": "user", "id": "u-signer" },
        "entities": [
            { "kind": "document", "id": "doc-55" }
        ],
        "payload": {}
    }
    await client.post("/v1/events", json=event_payload, headers=headers)

    # Query timeline
    response = await client.get("/v1/timeline?entity=document:doc-55", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data["events"]) == 1
    assert data["events"][0]["type"] == "doc.signed"

@pytest.mark.anyio
async def test_query_events_filter(client: AsyncClient):
    headers = {"X-Tenant-ID": "tenant-B"}
    
    # Create events
    await client.post("/v1/events", json={
        "idempotency_key": "filter-req-1",
        "occurred_at": "2025-02-01T10:00:00Z",
        "type": "login",
        "actor": { "kind": "user", "id": "u-200" },
        "entities": [],
        "payload": {}
    }, headers=headers)
    
    await client.post("/v1/events", json={
        "idempotency_key": "filter-req-2",
        "occurred_at": "2025-02-01T11:00:00Z",
        "type": "logout",
        "actor": { "kind": "user", "id": "u-200" },
        "entities": [],
        "payload": {}
    }, headers=headers)

    # Filter by type
    response = await client.get("/v1/events?type=login", headers=headers)
    data = response.json()
    assert len(data["events"]) == 1
    assert data["events"][0]["type"] == "login"
    
    # Filter by actor (assuming JSONB query works as implemented)
    # Note: This specific test depends on exact implementation details of JSONB querying in endpoints.py
    # If using .astext or similar operator, ensure keys match.
    response = await client.get("/v1/events?actor_id=u-200", headers=headers)
    data = response.json()
    assert len(data["events"]) == 2

