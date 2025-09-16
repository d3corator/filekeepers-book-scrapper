"""Tests for change detector."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime
from decimal import Decimal

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.scheduler.change_detector import ChangeDetector
from src.crawler.schemas import Book, ChangeLog


@pytest.mark.asyncio
async def test_change_detector_initialization():
    """Test change detector initialization."""
    detector = ChangeDetector()
    assert detector.storage is not None
    assert detector.crawler is not None


@pytest.mark.asyncio
async def test_compare_book_fields():
    """Test book field comparison."""
    detector = ChangeDetector()
    
    # Create test books
    stored_book = Book(
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
    
    current_book = Book(
        name="Test Book Updated",
        description="Updated description",
        category="Fiction",
        upc="123456789",
        price_including_tax=Decimal("24.99"),  # Price changed
        price_excluding_tax=Decimal("20.83"),
        tax_amount=Decimal("4.16"),
        availability="In stock (15 available)",  # Availability changed
        availability_count=15,
        number_of_reviews=7,  # Reviews changed
        rating=4,  # Rating changed
        image_url="http://example.com/image.jpg",
        url="http://example.com/book",
        crawl_timestamp=datetime.utcnow()
    )
    
    changes = detector._compare_book_fields(current_book, stored_book)
    
    # Check that changes were detected
    assert "name" in changes
    assert "description" in changes
    assert "price_including_tax" in changes
    assert "availability_count" in changes
    assert "number_of_reviews" in changes
    assert "rating" in changes
    
    # Check values
    assert changes["name"] == ("Test Book", "Test Book Updated")
    assert changes["price_including_tax"] == (Decimal("19.99"), Decimal("24.99"))
    assert changes["availability_count"] == (22, 15)


@pytest.mark.asyncio
async def test_compare_books_new_and_removed():
    """Test comparison with new and removed books."""
    detector = ChangeDetector()
    
    # Create test data
    current_books = {
        "http://example.com/book1": Book(
            name="Book 1",
            description="Description 1",
            category="Fiction",
            upc="111",
            price_including_tax=Decimal("10.00"),
            price_excluding_tax=Decimal("8.33"),
            tax_amount=Decimal("1.67"),
            availability="In stock",
            availability_count=5,
            number_of_reviews=0,
            rating=0,
            image_url="http://example.com/img1.jpg",
            url="http://example.com/book1",
            crawl_timestamp=datetime.utcnow()
        ),
        "http://example.com/book2": Book(
            name="Book 2",
            description="Description 2",
            category="Non-Fiction",
            upc="222",
            price_including_tax=Decimal("20.00"),
            price_excluding_tax=Decimal("16.67"),
            tax_amount=Decimal("3.33"),
            availability="In stock",
            availability_count=3,
            number_of_reviews=2,
            rating=4,
            image_url="http://example.com/img2.jpg",
            url="http://example.com/book2",
            crawl_timestamp=datetime.utcnow()
        )
    }
    
    stored_books = {
        "http://example.com/book1": Book(
            name="Book 1",
            description="Description 1",
            category="Fiction",
            upc="111",
            price_including_tax=Decimal("10.00"),
            price_excluding_tax=Decimal("8.33"),
            tax_amount=Decimal("1.67"),
            availability="In stock",
            availability_count=5,
            number_of_reviews=0,
            rating=0,
            image_url="http://example.com/img1.jpg",
            url="http://example.com/book1",
            crawl_timestamp=datetime.utcnow()
        ),
        "http://example.com/book3": Book(  # This book was removed
            name="Book 3",
            description="Description 3",
            category="Mystery",
            upc="333",
            price_including_tax=Decimal("15.00"),
            price_excluding_tax=Decimal("12.50"),
            tax_amount=Decimal("2.50"),
            availability="In stock",
            availability_count=1,
            number_of_reviews=1,
            rating=3,
            image_url="http://example.com/img3.jpg",
            url="http://example.com/book3",
            crawl_timestamp=datetime.utcnow()
        )
    }
    
    changes = await detector._compare_books(current_books, stored_books)
    
    # Check results
    assert len(changes["new_books"]) == 1
    assert len(changes["removed_books"]) == 1
    assert len(changes["updated_books"]) == 0
    assert changes["total_changes"] == 2
    
    # Check new book
    assert changes["new_books"][0].name == "Book 2"
    
    # Check removed book
    assert changes["removed_books"][0].name == "Book 3"
    
    # Check change logs
    assert len(changes["change_logs"]) == 2
    assert changes["change_logs"][0].change_type == "new"
    assert changes["change_logs"][1].change_type == "removed"


@pytest.mark.asyncio
async def test_generate_daily_report():
    """Test daily report generation."""
    detector = ChangeDetector()
    
    # Mock storage methods
    with patch.object(detector.storage, 'connect', new_callable=AsyncMock):
        with patch.object(detector.storage, 'disconnect', new_callable=AsyncMock):
            with patch.object(detector.storage, 'get_change_logs_by_date_range', new_callable=AsyncMock) as mock_get_logs:
                # Mock change logs
                mock_logs = [
                    ChangeLog(
                        book_id="123456789",
                        change_type="new",
                        field_changes={"book": {"old": None, "new": "New Book"}},
                        timestamp=datetime.utcnow()
                    ),
                    ChangeLog(
                        book_id="987654321",
                        change_type="updated",
                        field_changes={"price_including_tax": {"old": "10.00", "new": "12.00"}},
                        timestamp=datetime.utcnow()
                    )
                ]
                mock_get_logs.return_value = mock_logs
                
                report = await detector.generate_daily_report()
                
                # Check report structure
                assert "date" in report
                assert "total_changes" in report
                assert "new_books" in report
                assert "removed_books" in report
                assert "updated_books" in report
                assert "price_changes" in report
                assert "availability_changes" in report
                assert "changes_by_type" in report
                assert "top_changed_books" in report
                
                # Check values
                assert report["total_changes"] == 2
                assert report["new_books"] == 1
                assert report["price_changes"] == 1
                assert "new" in report["changes_by_type"]
                assert "updated" in report["changes_by_type"]
