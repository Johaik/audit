import pytest
import uuid
from httpx import AsyncClient
from sqlalchemy import text
from app.main import app
from app.api.deps import get_idp_provider
from app.config import settings
from tests.mocks import MockIdPProvider

# Fixture to override IdP
@pytest.fixture
def mock_idp():
    provider = MockIdPProvider()
    app.dependency_overrides[get_idp_provider] = lambda: provider
    yield provider
    app.dependency_overrides.pop(get_idp_provider, None)

@pytest.mark.asyncio
async def test_admin_register_tenant_success(client: AsyncClient, db_session, mock_idp):
    """
    Test registering a new tenant via the admin API.
    Should create a DB record and provision a Keycloak client (mocked).
    """
    admin_key = settings.ADMIN_API_KEY
    payload = {"name": "Test Tenant A"}
    
    response = await client.post(
        "/admin/tenants",
        json=payload,
        headers={"X-Admin-Key": admin_key}
    )
    
    assert response.status_code == 200, f"Response: {response.text}"
    data = response.json()
    assert data["name"] == "Test Tenant A"
    assert "id" in data
    assert "client_id" in data
    assert "client_secret" in data
    
    # Verify DB
    tenant_id = data["id"]
    result = await db_session.execute(text(f"SELECT * FROM tenants WHERE id = '{tenant_id}'"))
    row = result.fetchone()
    assert row is not None
    assert row.name == "Test Tenant A"

@pytest.mark.asyncio
async def test_admin_register_tenant_idp_failure_rollback(client: AsyncClient, db_session, mock_idp):
    """
    Test that if IdP provisioning fails, the DB record is rolled back.
    """
    admin_key = settings.ADMIN_API_KEY
    
    # Mock IdP to raise an exception
    def broken_create(*args, **kwargs):
        raise Exception("IdP Down")
    
    mock_idp.create_tenant_client = broken_create
    
    payload = {"name": "Broken Tenant"}
    response = await client.post(
        "/admin/tenants",
        json=payload,
        headers={"X-Admin-Key": admin_key}
    )
    
    assert response.status_code == 500
    assert "Failed to provision IdP" in response.text
    
    # Verify DB is empty (for this tenant name)
    result = await db_session.execute(text("SELECT * FROM tenants WHERE name = 'Broken Tenant'"))
    row = result.fetchone()
    assert row is None

@pytest.mark.asyncio
async def test_admin_auth_failure(client: AsyncClient):
    """
    Test admin API security.
    """
    payload = {"name": "Hacker Tenant"}
    
    # No Key
    response = await client.post("/admin/tenants", json=payload)
    assert response.status_code == 403
    
    # Wrong Key
    response = await client.post("/admin/tenants", json=payload, headers={"X-Admin-Key": "wrong-key"})
    assert response.status_code == 403

@pytest.mark.asyncio
async def test_rls_isolation_create_and_read(client: AsyncClient, mock_idp):
    """
    Deep test for RLS enforcement.
    1. Register Tenant A and Tenant B.
    2. Tenant A creates an event.
    3. Tenant B tries to read it -> Should Fail (404).
    4. Tenant A tries to read it -> Should Success.
    """
    admin_key = settings.ADMIN_API_KEY
    
    # 1. Register Tenants
    resp_a = await client.post("/admin/tenants", json={"name": "Tenant A"}, headers={"X-Admin-Key": admin_key})
    assert resp_a.status_code == 200
    tenant_a_id = resp_a.json()["id"]
    token_a = mock_idp.mint_token(tenant_a_id)
    
    resp_b = await client.post("/admin/tenants", json={"name": "Tenant B"}, headers={"X-Admin-Key": admin_key})
    assert resp_b.status_code == 200
    tenant_b_id = resp_b.json()["id"]
    token_b = mock_idp.mint_token(tenant_b_id)
    
    # 2. Tenant A creates an event
    event_payload = {
        "type": "user.login",
        "actor": {"kind": "user", "id": "u1"},
        "payload": {"ip": "1.2.3.4"},
        "idempotency_key": str(uuid.uuid4()),
        "occurred_at": "2025-01-01T12:00:00Z",
        "entities": [{"kind": "user", "id": "u1"}]
    }
    
    headers_a = {"Authorization": f"Bearer {token_a}"}
    create_resp = await client.post("/v1/events", json=event_payload, headers=headers_a)
    assert create_resp.status_code == 201, create_resp.text
    event_id = create_resp.json()["event_id"]
    
    # 3. Tenant B tries to read it
    headers_b = {"Authorization": f"Bearer {token_b}"}
    read_resp_b = await client.get(f"/v1/events/{event_id}", headers=headers_b)
    # RLS should filter this out, so it looks like it doesn't exist
    assert read_resp_b.status_code == 404
    
    # 4. Tenant A reads it
    read_resp_a = await client.get(f"/v1/events/{event_id}", headers=headers_a)
    assert read_resp_a.status_code == 200
    assert read_resp_a.json()["event_id"] == event_id

@pytest.mark.asyncio
async def test_rls_isolation_list(client: AsyncClient, mock_idp):
    """
    Verify that listing events only returns the tenant's own events.
    """
    admin_key = settings.ADMIN_API_KEY
    
    # Register Tenants
    resp1 = await client.post("/admin/tenants", json={"name": "T1"}, headers={"X-Admin-Key": admin_key})
    t1_id = resp1.json()["id"]
    
    resp2 = await client.post("/admin/tenants", json={"name": "T2"}, headers={"X-Admin-Key": admin_key})
    t2_id = resp2.json()["id"]
    
    token_t1 = mock_idp.mint_token(t1_id)
    token_t2 = mock_idp.mint_token(t2_id)
    
    # Create 2 events for T1
    for i in range(2):
        await client.post("/v1/events", json={
            "type": "test", "actor": {"kind": "k", "id": "i"}, 
            "payload": {}, "idempotency_key": f"t1-{i}", "occurred_at": "2025-01-01T10:00:00Z",
            "entities": []
        }, headers={"Authorization": f"Bearer {token_t1}"})

    # Create 1 event for T2
    await client.post("/v1/events", json={
        "type": "test", "actor": {"kind": "k", "id": "i"}, 
        "payload": {}, "idempotency_key": "t2-1", "occurred_at": "2025-01-01T10:00:00Z",
        "entities": []
    }, headers={"Authorization": f"Bearer {token_t2}"})
    
    # List events for T1
    list_t1 = await client.get("/v1/events", headers={"Authorization": f"Bearer {token_t1}"})
    assert list_t1.status_code == 200
    assert len(list_t1.json()["events"]) == 2
    
    # List events for T2
    list_t2 = await client.get("/v1/events", headers={"Authorization": f"Bearer {token_t2}"})
    assert list_t2.status_code == 200
    assert len(list_t2.json()["events"]) == 1

@pytest.mark.asyncio
async def test_rls_isolation_timeline(client: AsyncClient, mock_idp):
    """
    Verify that timeline endpoint respects RLS.
    """
    admin_key = settings.ADMIN_API_KEY
    resp1 = await client.post("/admin/tenants", json={"name": "TL1"}, headers={"X-Admin-Key": admin_key})
    t1_id = resp1.json()["id"]
    resp2 = await client.post("/admin/tenants", json={"name": "TL2"}, headers={"X-Admin-Key": admin_key})
    t2_id = resp2.json()["id"]
    
    token_t1 = mock_idp.mint_token(t1_id)
    token_t2 = mock_idp.mint_token(t2_id)
    
    entity = {"kind": "order", "id": "123"}
    
    # T1 creates event for order:123
    await client.post("/v1/events", json={
        "type": "order.created", "actor": {"kind": "sys", "id": "1"}, 
        "payload": {}, "idempotency_key": "e1", "occurred_at": "2025-01-01T10:00:00Z",
        "entities": [entity]
    }, headers={"Authorization": f"Bearer {token_t1}"})
    
    # T2 creates event for order:123 (Same entity ID, different tenant)
    await client.post("/v1/events", json={
        "type": "order.created", "actor": {"kind": "sys", "id": "1"}, 
        "payload": {}, "idempotency_key": "e2", "occurred_at": "2025-01-01T10:00:00Z",
        "entities": [entity]
    }, headers={"Authorization": f"Bearer {token_t2}"})
    
    # T1 requests timeline for order:123 -> Should get 1 event
    resp_t1 = await client.get(f"/v1/timeline?entity=order:123", headers={"Authorization": f"Bearer {token_t1}"})
    assert resp_t1.status_code == 200
    assert len(resp_t1.json()["events"]) == 1
    
    # T2 requests timeline for order:123 -> Should get 1 event
    resp_t2 = await client.get(f"/v1/timeline?entity=order:123", headers={"Authorization": f"Bearer {token_t2}"})
    assert resp_t2.status_code == 200
    assert len(resp_t2.json()["events"]) == 1
    assert resp_t2.json()["events"][0]["tenant_id"] == t2_id

@pytest.mark.asyncio
async def test_cross_tenant_idempotency(client: AsyncClient, mock_idp):
    """
    Verify that different tenants can use the same idempotency key.
    """
    admin_key = settings.ADMIN_API_KEY
    resp1 = await client.post("/admin/tenants", json={"name": "I1"}, headers={"X-Admin-Key": admin_key})
    t1_id = resp1.json()["id"]
    resp2 = await client.post("/admin/tenants", json={"name": "I2"}, headers={"X-Admin-Key": admin_key})
    t2_id = resp2.json()["id"]
    
    token_t1 = mock_idp.mint_token(t1_id)
    token_t2 = mock_idp.mint_token(t2_id)
    
    idem_key = "shared-key-123"
    
    # T1 creates event
    r1 = await client.post("/v1/events", json={
        "type": "test", "actor": {"kind": "k", "id": "i"}, 
        "payload": {"v": 1}, "idempotency_key": idem_key, "occurred_at": "2025-01-01T10:00:00Z",
        "entities": []
    }, headers={"Authorization": f"Bearer {token_t1}"})
    assert r1.status_code == 201
    
    # T2 creates event with SAME key -> Should Succeed (Unique per tenant)
    r2 = await client.post("/v1/events", json={
        "type": "test", "actor": {"kind": "k", "id": "i"}, 
        "payload": {"v": 2}, "idempotency_key": idem_key, "occurred_at": "2025-01-01T10:00:00Z",
        "entities": []
    }, headers={"Authorization": f"Bearer {token_t2}"})
    assert r2.status_code == 201
    
    # T1 creates event with SAME key -> Should be idempotent (return existing)
    r3 = await client.post("/v1/events", json={
        "type": "test", "actor": {"kind": "k", "id": "i"}, 
        "payload": {"v": 1}, "idempotency_key": idem_key, "occurred_at": "2025-01-01T10:00:00Z",
        "entities": []
    }, headers={"Authorization": f"Bearer {token_t1}"})
    assert r3.status_code == 200
    assert r3.json()["event_id"] == r1.json()["event_id"]

@pytest.mark.asyncio
async def test_auth_missing_tenant_context(client: AsyncClient, mock_idp):
    """
    Test that a valid token without 'tid' claim is rejected.
    """
    token = "bad-token"
    mock_idp.tokens[token] = {"sub": "user", "scope": "read"} # No 'tid'
    
    response = await client.get("/v1/events", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403
    assert "Token missing tenant context" in response.json()["detail"]

@pytest.mark.asyncio
async def test_auth_invalid_token(client: AsyncClient, mock_idp):
    response = await client.get("/v1/events", headers={"Authorization": "Bearer invalid-jwt"})
    assert response.status_code == 401
