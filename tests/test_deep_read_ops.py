import pytest
from httpx import AsyncClient
import asyncio
from datetime import datetime, timedelta

@pytest.mark.anyio
async def test_timeline_ordering_and_pagination(client: AsyncClient, auth_headers):
    """
    Test that timeline returns events in correct order (descending occurred_at)
    and pagination works correctly.
    """
    tenant_id = "tenant-timeline-1"
    headers = auth_headers(tenant_id)
    entity = { "kind": "order", "id": "ord-1" }
    
    # Create 5 events with different timestamps
    base_time = datetime(2025, 1, 1, 12, 0, 0)
    for i in range(5):
        dt = base_time + timedelta(minutes=i)
        payload = {
            "idempotency_key": f"order-ev-{i}",
            "occurred_at": dt.isoformat() + "Z",
            "type": f"order.step.{i}",
            "actor": { "kind": "sys", "id": "bot" },
            "entities": [entity],
            "payload": { "step": i }
        }
        resp = await client.post("/v1/events", json=payload, headers=headers)
        assert resp.status_code == 201

    # Fetch page 1 (limit 2)
    resp = await client.get(f"/v1/timeline?entity=order:ord-1&limit=2", headers=headers)
    data = resp.json()
    assert len(data["events"]) == 2
    # Should be the latest ones: step 4 and step 3
    assert data["events"][0]["type"] == "order.step.4"
    assert data["events"][1]["type"] == "order.step.3"
    assert data["next_cursor"] is not None
    
    cursor = data["next_cursor"]
    
    # Fetch page 2 (limit 2)
    resp = await client.get(f"/v1/timeline?entity=order:ord-1&limit=2&cursor={cursor}", headers=headers)
    assert resp.status_code == 200, f"Failed pagination request: {resp.text}"
    data = resp.json()
    assert len(data["events"]) == 2
    # Should be step 2 and step 1
    assert data["events"][0]["type"] == "order.step.2"
    assert data["events"][1]["type"] == "order.step.1"
    
    cursor = data["next_cursor"]

    # Fetch page 3 (limit 2, only 1 left)
    resp = await client.get(f"/v1/timeline?entity=order:ord-1&limit=2&cursor={cursor}", headers=headers)
    data = resp.json()
    assert len(data["events"]) == 1
    assert data["events"][0]["type"] == "order.step.0"
    # No next cursor
    assert data["next_cursor"] is None

@pytest.mark.anyio
async def test_timeline_mixed_entities(client: AsyncClient, auth_headers):
    """
    Verify timeline only shows events for the requested entity.
    """
    headers = auth_headers("tenant-timeline-2")
    
    # Event 1: Linked to User A
    await client.post("/v1/events", json={
        "idempotency_key": "ev-1",
        "occurred_at": "2025-01-01T10:00:00Z",
        "type": "user.update",
        "actor": { "kind": "admin", "id": "a1" },
        "entities": [{ "kind": "user", "id": "A" }],
        "payload": {}
    }, headers=headers)

    # Event 2: Linked to User B
    await client.post("/v1/events", json={
        "idempotency_key": "ev-2",
        "occurred_at": "2025-01-01T10:05:00Z",
        "type": "user.update",
        "actor": { "kind": "admin", "id": "a1" },
        "entities": [{ "kind": "user", "id": "B" }],
        "payload": {}
    }, headers=headers)

    # Event 3: Linked to User A AND User B
    await client.post("/v1/events", json={
        "idempotency_key": "ev-3",
        "occurred_at": "2025-01-01T10:10:00Z",
        "type": "group.add",
        "actor": { "kind": "admin", "id": "a1" },
        "entities": [{ "kind": "user", "id": "A" }, { "kind": "user", "id": "B" }],
        "payload": {}
    }, headers=headers)

    # Query User A Timeline -> Should see Event 3 and Event 1
    resp = await client.get("/v1/timeline?entity=user:A", headers=headers)
    events_a = resp.json()["events"]
    assert len(events_a) == 2
    assert events_a[0]["type"] == "group.add"
    assert events_a[1]["type"] == "user.update"

    # Query User B Timeline -> Should see Event 3 and Event 2
    resp = await client.get("/v1/timeline?entity=user:B", headers=headers)
    events_b = resp.json()["events"]
    assert len(events_b) == 2
    assert events_b[0]["type"] == "group.add"
    assert events_b[1]["type"] == "user.update"

@pytest.mark.anyio
async def test_events_list_filtering(client: AsyncClient, auth_headers):
    """
    Test filtering the main events list (by type, actor, etc).
    """
    headers = auth_headers("tenant-events-1")
    
    # Setup data
    events = [
        ("t1", "login", "user", "u1"),
        ("t2", "view", "user", "u1"),
        ("t3", "logout", "user", "u1"),
        ("t4", "login", "user", "u2"),
    ]
    
    base_time = datetime(2025, 2, 1, 10, 0, 0)
    for i, (key, type_, a_kind, a_id) in enumerate(events):
        dt = base_time + timedelta(minutes=i)
        await client.post("/v1/events", json={
            "idempotency_key": key,
            "occurred_at": dt.isoformat() + "Z",
            "type": type_,
            "actor": { "kind": a_kind, "id": a_id },
            "entities": [],
            "payload": {}
        }, headers=headers)

    # Filter by Type
    resp = await client.get("/v1/events?type=login", headers=headers)
    data = resp.json()
    assert len(data["events"]) == 2
    assert all(e["type"] == "login" for e in data["events"])

    # Filter by Actor ID
    resp = await client.get("/v1/events?actor_id=u1", headers=headers)
    data = resp.json()
    assert len(data["events"]) == 3
    assert all(e["actor"]["id"] == "u1" for e in data["events"])
    
    # Filter by Actor ID + Type
    resp = await client.get("/v1/events?actor_id=u1&type=login", headers=headers)
    data = resp.json()
    assert len(data["events"]) == 1
    assert data["events"][0]["idempotency_key"] == "t1"

