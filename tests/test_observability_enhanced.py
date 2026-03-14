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
    from app.api.endpoints import logger as api_logger
    
    # Check if structlog is used by inspecting the logger or its handlers
    # Actually, we want to see if structlog.get_logger() returns a structlog logger.
    assert isinstance(structlog.get_logger(), structlog.BoundLogger)
    
    # Trigger an ingestion request to generate logs
    # (Functional correctness is tested elsewhere, we just care about log format here)
    # Since we can't easily capture uvicorn's stdout in this test context,
    # we'll check if structlog is configured.
    
    processors = structlog.get_config()["processors"]
    assert any("JSONRenderer" in str(p) for p in processors), "JSONRenderer not found in structlog processors"
