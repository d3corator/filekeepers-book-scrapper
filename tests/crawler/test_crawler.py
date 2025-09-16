import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, patch
from src.crawler.crawler import BookCrawler
from src.crawler.schemas import Book


@pytest.mark.asyncio
async def test_crawler_initialization():
    """Test crawler initialization"""
    crawler = BookCrawler()
    assert crawler.session_id is not None
    assert len(crawler.crawled_urls) == 0
    assert len(crawler.failed_urls) == 0


@pytest.mark.asyncio
async def test_parse_book_page():
    """Test book page parsing"""
    crawler = BookCrawler()
    
    # Sample HTML content
    html_content = """
    <html>
        <head><title>Test Book</title></head>
        <body>
            <h1>Test Book Title</h1>
            <p id="product_description">Description</p>
            <p class="price_color">£19.99</p>
            <p class="availability">In stock (22 available)</p>
            <div class="item active">
                <img src="/media/test.jpg" alt="Test Book">
            </div>
            <p class="star-rating Three"></p>
            <ul class="breadcrumb">
                <li><a href="/">Home</a></li>
                <li><a href="/category">Fiction</a></li>
            </ul>
            <table class="table">
                <tr><td>UPC</td><td>123456789</td></tr>
                <tr><td>Price (excl. tax)</td><td>£16.66</td></tr>
                <tr><td>Number of reviews</td><td>5</td></tr>
            </table>
        </body>
    </html>
    """
    
    book = await crawler._parse_book_page("https://test.com/book", html_content)
    
    assert book is not None
    assert book.name == "Test Book Title"
    assert book.category == "Fiction"
    assert book.upc == "123456789"
    assert book.price_including_tax == Decimal('19.99')
    assert book.price_excluding_tax == Decimal('16.66')
    assert book.tax_amount == Decimal('3.33')
    assert book.availability_count == 22
    assert book.rating == 3
    assert book.number_of_reviews == 5
