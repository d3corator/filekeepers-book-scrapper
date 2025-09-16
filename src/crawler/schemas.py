from __future__ import annotations

import hashlib
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, computed_field, validator


class Book(BaseModel):
    """Book schema for storing book information from books.toscrape.com"""
    
    # Basic book information
    name: str = Field(..., description="Name of the book")
    description: str = Field(..., description="Description of the book")
    category: str = Field(..., description="Book category")
    upc: str = Field(..., description="Universal Product Code")
    
    # Pricing information
    price_including_tax: Decimal = Field(..., description="Price including tax")
    price_excluding_tax: Decimal = Field(..., description="Price excluding tax")
    tax_amount: Decimal = Field(..., description="Tax amount")
    
    # Availability and reviews
    availability: str = Field(..., description="Availability status")
    availability_count: int = Field(..., ge=0, description="Number of books available")
    number_of_reviews: int = Field(..., ge=0, description="Number of reviews")
    
    # Media and rating
    image_url: str = Field(..., description="URL of the book cover image")
    rating: int = Field(..., ge=0, le=5, description="Rating of the book (0-5 stars)")
    
    # Metadata
    url: str = Field(..., description="Source URL of the book page")
    crawl_timestamp: datetime = Field(default_factory=datetime.utcnow, description="When this book was crawled")
    status: str = Field(default="crawled", description="Crawl status")
    
    # Raw HTML snapshot for fallback
    raw_html: Optional[str] = Field(None, description="Raw HTML snapshot of the book page")
    
    @computed_field
    @property
    def content_hash(self) -> str:
        """Generate a hash of the book content for change detection"""
        content = f"{self.name}{self.description}{self.upc}{self.price_including_tax}{self.price_excluding_tax}{self.tax_amount}{self.availability}{self.availability_count}{self.number_of_reviews}{self.rating}"
        return hashlib.md5(content.encode()).hexdigest()
    
    @validator('price_including_tax', 'price_excluding_tax', 'tax_amount', pre=True)
    def parse_price(cls, v):
        """Parse price strings to Decimal"""
        if isinstance(v, str):
            # Remove currency symbols and convert to Decimal
            v = v.replace('£', '').replace('$', '').replace(',', '').strip()
            return Decimal(v)
        return v
    
    @validator('number_of_reviews', 'availability_count', pre=True)
    def parse_reviews(cls, v):
        """Parse number of reviews from string"""
        if isinstance(v, str):
            return int(v) if v.isdigit() else 0
        return v
    
    @validator('rating', pre=True)
    def parse_rating(cls, v):
        """Parse rating from string (e.g., 'Three' -> 3)"""
        if isinstance(v, str):
            rating_map = {
                'Zero': 0, 'One': 1, 'Two': 2, 'Three': 3, 'Four': 4, 'Five': 5
            }
            return rating_map.get(v, 0)
        return v
    
    class Config:
        json_encoders = {
            Decimal: str,
            datetime: lambda v: v.isoformat()
        }


class CrawlSession(BaseModel):
    """Schema for tracking crawl sessions"""
    
    session_id: str = Field(..., description="Unique session identifier")
    started_at: datetime = Field(default_factory=datetime.utcnow, description="When the crawl started")
    completed_at: Optional[datetime] = Field(None, description="When the crawl completed")
    status: str = Field(default="running", description="Session status: running, completed, failed")
    total_books_found: int = Field(default=0, description="Total number of books found")
    books_crawled: int = Field(default=0, description="Number of books successfully crawled")
    books_failed: int = Field(default=0, description="Number of books that failed to crawl")
    last_crawled_url: Optional[str] = Field(None, description="Last successfully crawled URL")
    error_message: Optional[str] = Field(None, description="Error message if crawl failed")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ChangeLog(BaseModel):
    """Schema for tracking changes to books"""
    
    book_id: str = Field(..., description="ID of the book that changed")
    change_type: str = Field(..., description="Type of change: new, updated, deleted")
    field_changes: dict = Field(default_factory=dict, description="Fields that changed and their old/new values")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="When the change was detected")
    session_id: Optional[str] = Field(None, description="Crawl session that detected the change")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
