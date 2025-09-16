"""Tests for change endpoints."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from src.api.app import app
from src.crawler.schemas import ChangeLog
from datetime import datetime

client = TestClient(app)


@pytest.fixture
def mock_change_log():
    """Create a mock change log for testing."""
    return ChangeLog(
        book_id="123456789",
        change_type="updated",
        field_changes={"price_including_tax": {"old": "19.99", "new": "24.99"}},
        timestamp=datetime.utcnow()
    )


def test_get_changes_without_api_key():
    """Test getting changes without API key."""
    response = client.get("/api/v1/changes")
    assert response.status_code == 403


def test_get_changes_with_invalid_api_key():
    """Test getting changes with invalid API key."""
    response = client.get(
        "/api/v1/changes",
        headers={"Authorization": "Bearer invalid-key"}
    )
    assert response.status_code == 401


def test_get_changes_success(mock_change_log):
    """Test successful changes retrieval."""
    # Mock storage
    mock_storage = AsyncMock()
    mock_storage.get_change_logs_paginated.return_value = [mock_change_log]
    mock_storage.get_change_logs_count.return_value = 1
    mock_storage.disconnect.return_value = None
    
    # Override the dependency
    from src.api.routers.changes import get_storage
    app.dependency_overrides[get_storage] = lambda: mock_storage
    
    response = client.get(
        "/api/v1/changes",
        headers={"Authorization": "Bearer default-api-key"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "changes" in data
    assert "total" in data
    assert "page" in data
    assert "per_page" in data
    assert "total_pages" in data
    assert "has_next" in data
    assert "has_prev" in data
    assert len(data["changes"]) == 1
    assert data["changes"][0]["book_id"] == "123456789"
    
    # Clean up dependency override
    app.dependency_overrides.clear()


def test_get_changes_with_filters(mock_change_log):
    """Test getting changes with filters."""
    # Mock storage
    mock_storage = AsyncMock()
    mock_storage.get_change_logs_paginated.return_value = [mock_change_log]
    mock_storage.get_change_logs_count.return_value = 1
    mock_storage.disconnect.return_value = None
    
    # Override the dependency
    from src.api.routers.changes import get_storage
    app.dependency_overrides[get_storage] = lambda: mock_storage
    
    response = client.get(
        "/api/v1/changes?change_type=updated&book_id=123456789",
        headers={"Authorization": "Bearer default-api-key"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert len(data["changes"]) == 1
    assert data["changes"][0]["change_type"] == "updated"
    
    # Clean up dependency override
    app.dependency_overrides.clear()


def test_get_changes_pagination(mock_change_log):
    """Test changes pagination."""
    # Mock storage
    mock_storage = AsyncMock()
    mock_storage.get_change_logs_paginated.return_value = [mock_change_log]
    mock_storage.get_change_logs_count.return_value = 25
    mock_storage.disconnect.return_value = None
    
    # Override the dependency
    from src.api.routers.changes import get_storage
    app.dependency_overrides[get_storage] = lambda: mock_storage
    
    response = client.get(
        "/api/v1/changes?page=2&per_page=10",
        headers={"Authorization": "Bearer default-api-key"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["page"] == 2
    assert data["per_page"] == 10
    assert data["total"] == 25
    assert data["total_pages"] == 3
    assert data["has_next"] is True
    assert data["has_prev"] is True
    
    # Clean up dependency override
    app.dependency_overrides.clear()
