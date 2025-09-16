"""API request/response schemas."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field


class BookResponse(BaseModel):
    """Book response schema for API."""
    
    name: str = Field(..., description="Name of the book")
    description: str = Field(..., description="Description of the book")
    category: str = Field(..., description="Book category")
    upc: str = Field(..., description="Universal Product Code")
    price_including_tax: Decimal = Field(..., description="Price including tax")
    price_excluding_tax: Decimal = Field(..., description="Price excluding tax")
    tax_amount: Decimal = Field(..., description="Tax amount")
    availability: str = Field(..., description="Availability status")
    availability_count: int = Field(..., description="Number of books available")
    number_of_reviews: int = Field(..., description="Number of reviews")
    rating: int = Field(..., description="Rating (0-5 stars)")
    image_url: str = Field(..., description="URL of the book cover image")
    url: str = Field(..., description="URL of the book page")
    crawl_timestamp: datetime = Field(..., description="When the book was crawled")
    
    class Config:
        json_encoders = {
            Decimal: lambda v: float(v),
            datetime: lambda v: v.isoformat()
        }


class BookListResponse(BaseModel):
    """Book list response with pagination."""
    
    books: List[BookResponse] = Field(..., description="List of books")
    total: int = Field(..., description="Total number of books")
    page: int = Field(..., description="Current page number")
    per_page: int = Field(..., description="Number of books per page")
    total_pages: int = Field(..., description="Total number of pages")
    has_next: bool = Field(..., description="Whether there is a next page")
    has_prev: bool = Field(..., description="Whether there is a previous page")


class ChangeLogResponse(BaseModel):
    """Change log response schema."""
    
    book_id: str = Field(..., description="ID of the book that changed")
    change_type: str = Field(..., description="Type of change: new, updated, removed")
    field_changes: dict = Field(..., description="Fields that changed and their old/new values")
    timestamp: datetime = Field(..., description="When the change was detected")
    session_id: Optional[str] = Field(None, description="Crawl session that detected the change")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ChangeListResponse(BaseModel):
    """Change list response with pagination."""
    
    changes: List[ChangeLogResponse] = Field(..., description="List of changes")
    total: int = Field(..., description="Total number of changes")
    page: int = Field(..., description="Current page number")
    per_page: int = Field(..., description="Number of changes per page")
    total_pages: int = Field(..., description="Total number of pages")
    has_next: bool = Field(..., description="Whether there is a next page")
    has_prev: bool = Field(..., description="Whether there is a previous page")


class BookFilters(BaseModel):
    """Book filtering parameters."""
    
    category: Optional[str] = Field(None, description="Filter by category")
    min_price: Optional[float] = Field(None, ge=0, description="Minimum price")
    max_price: Optional[float] = Field(None, ge=0, description="Maximum price")
    rating: Optional[int] = Field(None, ge=0, le=5, description="Filter by rating")
    sort_by: Optional[str] = Field("name", description="Sort by field (name, price_including_tax, rating, number_of_reviews)")
    sort_order: Optional[str] = Field("asc", description="Sort order (asc, desc)")


class HealthResponse(BaseModel):
    """Health check response."""
    
    status: str = Field(..., description="Service status")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Current timestamp")
    version: str = Field("0.1.0", description="API version")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ErrorResponse(BaseModel):
    """Error response schema."""
    
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
