"""
Tests for FastAPI endpoints.
Starts with health check, will expand to auth, tenants, etc. in later weeks.
"""

import pytest


@pytest.mark.asyncio
async def test_health_check(test_client):
    """Test the health check endpoint."""
    response = await test_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["environment"] in ["development", "staging", "production"]
    assert "version" in data
