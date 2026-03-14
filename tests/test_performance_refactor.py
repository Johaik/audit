import pytest
from httpx import AsyncClient
import uuid
from sqlalchemy import select, text
from app.models import Event
from unittest.mock import MagicMock, patch

@pytest.mark.anyio
async def test_idempotency_functional_success(client: AsyncClient, auth_headers):
    """
    Standard functional test: identical requests should return 200 and the same object.
    """
    payload = {
        "idempotency_key": f"perf-test-{uuid.uuid4()}",
        "occurred_at": "2025-12-19T10:11:12Z",
        "type": "perf.test",
        "actor": { "kind": "user", "id": "u1" },
        "entities": [],
        "payload": { "data": "original" }
    }
    headers = auth_headers("tenant-perf")

    # First request
    resp1 = await client.post("/v1/events", json=payload, headers=headers)
    assert resp1.status_code == 201
    id1 = resp1.json()["event_id"]

    # Second request
    resp2 = await client.post("/v1/events", json=payload, headers=headers)
    assert resp2.status_code == 200
    assert resp2.json()["event_id"] == id1

@pytest.mark.anyio
async def test_idempotency_functional_conflict(client: AsyncClient, auth_headers):
    """
    Functional test: same idempotency key but different payload should return 409.
    """
    key = f"perf-conflict-{uuid.uuid4()}"
    headers = auth_headers("tenant-perf")
    
    payload1 = {
        "idempotency_key": key,
        "occurred_at": "2025-12-19T10:11:12Z",
        "type": "perf.test",
        "actor": { "kind": "user", "id": "u1" },
        "entities": [],
        "payload": { "data": "original" }
    }
    
    payload2 = payload1.copy()
    payload2["payload"] = { "data": "modified" }

    await client.post("/v1/events", json=payload1, headers=headers)
    
    resp2 = await client.post("/v1/events", json=payload2, headers=headers)
    assert resp2.status_code == 409

@pytest.mark.anyio
async def test_verify_savepoint_usage(client: AsyncClient, auth_headers):
    """
    This test specifically checks that 'begin_nested' (SAVEPOINT) is currently used.
    It will FAIL once we refactor to ON CONFLICT, which is what we want (to confirm we changed it).
    Wait, the instruction says: "Ensure tests fail if existing savepoint logic is missing or broken."
    Actually, it probably means if I BREAK the logic during the refactor.
    
    But to be sure I am testing the RIGHT thing now, I'll use a spy on the session.
    """
    from sqlalchemy.ext.asyncio import AsyncSession
    
    # We need to spy on the session used inside the app.
    # The 'client' fixture overrides 'get_db' in app.main.
    
    spy = MagicMock()
    
    original_begin_nested = AsyncSession.begin_nested
    
    def mocked_begin_nested(self):
        spy()
        return original_begin_nested(self)

    payload = {
        "idempotency_key": f"spy-test-{uuid.uuid4()}",
        "occurred_at": "2025-12-19T10:11:12Z",
        "type": "perf.test",
        "actor": { "kind": "user", "id": "u1" },
        "entities": [],
        "payload": { "data": "spy" }
    }
    headers = auth_headers("tenant-perf")

    with patch("sqlalchemy.ext.asyncio.AsyncSession.begin_nested", autospec=True, side_effect=mocked_begin_nested):
        resp = await client.post("/v1/events", json=payload, headers=headers)
        assert resp.status_code == 201
        assert spy.called, "Existing savepoint logic (begin_nested) was NOT called!"

@pytest.mark.anyio
async def test_idempotency_multi_tenant_isolation(client: AsyncClient, auth_headers):
    """
    Ensure idempotency key is scoped per tenant.
    """
    key = f"shared-key-{uuid.uuid4()}"
    payload = {
        "idempotency_key": key,
        "occurred_at": "2025-12-19T10:11:12Z",
        "type": "perf.test",
        "actor": { "kind": "user", "id": "u1" },
        "entities": [],
        "payload": { "data": "shared" }
    }
    
    # Tenant A
    resp1 = await client.post("/v1/events", json=payload, headers=auth_headers("tenant-A"))
    assert resp1.status_code == 201
    
    # Tenant B
    resp2 = await client.post("/v1/events", json=payload, headers=auth_headers("tenant-B"))
    assert resp2.status_code == 201
    assert resp1.json()["event_id"] != resp2.json()["event_id"]
