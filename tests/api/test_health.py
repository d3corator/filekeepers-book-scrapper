"""Tests for health endpoints."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest
from fastapi.testclient import TestClient

from src.api.app import app

client = TestClient(app)


def test_health_check():
    """Test health check endpoint."""
    response = client.get("/api/v1/health")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["version"] == "0.1.0"
    assert "timestamp" in data


def test_health_check_rate_limit():
    """Test health check rate limiting."""
    # Make multiple requests to test rate limiting
    responses = []
    for _ in range(5):
        response = client.get("/api/v1/health")
        responses.append(response)
    
    # All should succeed (rate limit is 100/hour)
    for response in responses:
        assert response.status_code == 200
