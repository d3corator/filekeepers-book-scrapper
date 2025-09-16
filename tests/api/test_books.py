"""Tests for book endpoints."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from src.api.app import app
from src.crawler.schemas import Book
from datetime import datetime
from decimal import Decimal

client = TestClient(app)


@pytest.fixture
def mock_book():
    """Create a mock book for testing."""
    return Book(
        name="Test Book",
        description="Test description",
        category="Fiction",
        upc="123456789",
        price_including_tax=Decimal("19.99"),
        price_excluding_tax=Decimal("16.66"),
        tax_amount=Decimal("3.33"),
        availability="In stock (22 available)",
        availability_count=22,
        number_of_reviews=5,
        rating=3,
        image_url="http://example.com/image.jpg",
        url="http://example.com/book",
        crawl_timestamp=datetime.utcnow()
    )


def test_get_books_without_api_key():
    """Test getting books without API key."""
    response = client.get("/api/v1/books")
    assert response.status_code == 403


def test_get_books_with_invalid_api_key():
    """Test getting books with invalid API key."""
    response = client.get(
        "/api/v1/books",
        headers={"Authorization": "Bearer invalid-key"}
    )
    assert response.status_code == 401


def test_get_books_success(mock_book):
    """Test successful book retrieval."""
    # Mock storage
    mock_storage = AsyncMock()
    mock_storage.get_books_paginated.return_value = [mock_book]
    mock_storage.get_books_count.return_value = 1
    mock_storage.disconnect.return_value = None
    
    # Override the dependency
    from src.api.routers.books import get_storage
    app.dependency_overrides[get_storage] = lambda: mock_storage
    
    response = client.get(
        "/api/v1/books",
        headers={"Authorization": "Bearer default-api-key"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "books" in data
    assert "total" in data
    assert "page" in data
    assert "per_page" in data
    assert "total_pages" in data
    assert "has_next" in data
    assert "has_prev" in data
    assert len(data["books"]) == 1
    assert data["books"][0]["name"] == "Test Book"
    
    # Clean up dependency override
    app.dependency_overrides.clear()


def test_get_books_with_filters(mock_book):
    """Test getting books with filters."""
    # Mock storage
    mock_storage = AsyncMock()
    mock_storage.get_books_paginated.return_value = [mock_book]
    mock_storage.get_books_count.return_value = 1
    mock_storage.disconnect.return_value = None
    
    # Override the dependency
    from src.api.routers.books import get_storage
    app.dependency_overrides[get_storage] = lambda: mock_storage
    
    response = client.get(
        "/api/v1/books?category=Fiction&min_price=10&max_price=30&rating=3",
        headers={"Authorization": "Bearer default-api-key"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert len(data["books"]) == 1
    
    # Clean up dependency override
    app.dependency_overrides.clear()


def test_get_book_by_id_success(mock_book):
    """Test successful book retrieval by ID."""
    # Mock storage
    mock_storage = AsyncMock()
    mock_storage.get_book_by_upc.return_value = mock_book
    mock_storage.disconnect.return_value = None
    
    # Override the dependency
    from src.api.routers.books import get_storage
    app.dependency_overrides[get_storage] = lambda: mock_storage
    
    response = client.get(
        "/api/v1/books/123456789",
        headers={"Authorization": "Bearer default-api-key"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Book"
    assert data["upc"] == "123456789"
    
    # Clean up dependency override
    app.dependency_overrides.clear()


def test_get_book_by_id_not_found():
    """Test book not found by ID."""
    # Mock storage
    mock_storage = AsyncMock()
    mock_storage.get_book_by_upc.return_value = None
    mock_storage.disconnect.return_value = None
    
    # Override the dependency
    from src.api.routers.books import get_storage
    app.dependency_overrides[get_storage] = lambda: mock_storage
    
    response = client.get(
        "/api/v1/books/nonexistent",
        headers={"Authorization": "Bearer default-api-key"}
    )
    
    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["error"].lower()
    
    # Clean up dependency override
    app.dependency_overrides.clear()
