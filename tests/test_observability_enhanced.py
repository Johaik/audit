import pytest
from httpx import AsyncClient
import json
import logging
from unittest.mock import patch, MagicMock

@pytest.mark.anyio
async def test_health_check_detailed(client: AsyncClient):
    """
    Test that the health check returns detailed information.
    Currently it only returns {"status": "ok"}.
    This test expects more.
    """
    response = await client.get("/health")
    data = response.json()
    assert response.status_code == 200, f"Status code: {response.status_code}, data: {data}"
    assert data["status"] == "ok", f"Health check failed: {data}"
    assert "components" in data
    assert "postgres" in data["components"]
    assert "keycloak" in data["components"]
    assert "latency_ms" in data["components"]["postgres"]

@pytest.mark.anyio
async def test_structured_logging_output(client: AsyncClient, capsys):
    """
    Test that logs are output in structured JSON format.
    We'll trigger a request that logs something and check stdout.
    Note: Testing stdout/stderr in async tests with uvicorn can be tricky,
    so we might need to mock the logger or check the configured handlers.
    """
    import structlog
    from app.core.logging import setup_logging
    
    # Ensure logging is setup (might have already been called in app)
    setup_logging()
    
    # Trigger a log call to ensure the proxy is initialized if needed
    log = structlog.get_logger()
    log.info("test log")
    
    # Check configuration
    conf = structlog.get_config()
    assert conf["logger_factory"] is not None
    
    # Verify JSONRenderer is in processors
    processors = conf["processors"]
    assert any("JSONRenderer" in str(p) for p in processors), f"JSONRenderer not found in {processors}"

@pytest.mark.anyio
async def test_tracing_context_propagation(client: AsyncClient, auth_headers):
    """
    Test that trace ID is present in response headers and propagated.
    This test expects OpenTelemetry instrumentation to be active.
    """
    # Use a traced endpoint (not health)
    response = await client.get("/v1/events", headers=auth_headers("tenant-trace"))
    assert response.status_code == 200
    
    # Check for trace ID in headers. 
    assert "X-Trace-Id" in response.headers or "traceparent" in response.headers
    if "X-Trace-Id" in response.headers:
        trace_id = response.headers["X-Trace-Id"]
        assert len(trace_id) == 32
        assert trace_id != "00000000000000000000000000000000"
