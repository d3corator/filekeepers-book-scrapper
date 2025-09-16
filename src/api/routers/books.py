"""Book-related API endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.api.auth import verify_api_key
from src.api.schemas import BookFilters, BookListResponse, BookResponse
from src.crawler.storage import MongoDBStorage

router = APIRouter()


async def get_storage() -> MongoDBStorage:
    """Get MongoDB storage instance."""
    storage = MongoDBStorage()
    await storage.connect()
    return storage


@router.get("/books", response_model=BookListResponse)
async def get_books(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    category: Optional[str] = Query(None, description="Filter by category"),
    min_price: Optional[float] = Query(None, ge=0, description="Minimum price"),
    max_price: Optional[float] = Query(None, ge=0, description="Maximum price"),
    rating: Optional[int] = Query(None, ge=0, le=5, description="Filter by rating"),
    sort_by: str = Query("name", description="Sort by field"),
    sort_order: str = Query("asc", description="Sort order (asc/desc)"),
    api_key: str = Depends(verify_api_key),
    storage: MongoDBStorage = Depends(get_storage)
):
    """Get books with filtering and pagination."""
    try:
        # Build filter query
        filter_query = {}
        
        if category:
            filter_query["category"] = {"$regex": category, "$options": "i"}
        
        if min_price is not None or max_price is not None:
            price_filter = {}
            if min_price is not None:
                price_filter["$gte"] = min_price
            if max_price is not None:
                price_filter["$lte"] = max_price
            filter_query["price_including_tax"] = price_filter
        
        if rating is not None:
            filter_query["rating"] = rating
        
        # Build sort query
        sort_direction = 1 if sort_order == "asc" else -1
        sort_query = [(sort_by, sort_direction)]
        
        # Calculate pagination
        skip = (page - 1) * per_page
        
        # Get total count
        total = await storage.get_books_count()
        
        # Get books with pagination
        books = await storage.get_books_paginated(
            filter_query=filter_query,
            sort_query=sort_query,
            skip=skip,
            limit=per_page
        )
        
        # Convert Book objects to BookResponse objects
        book_responses = [
            BookResponse(
                name=book.name,
                description=book.description,
                category=book.category,
                upc=book.upc,
                price_including_tax=book.price_including_tax,
                price_excluding_tax=book.price_excluding_tax,
                tax_amount=book.tax_amount,
                availability=book.availability,
                availability_count=book.availability_count,
                number_of_reviews=book.number_of_reviews,
                rating=book.rating,
                image_url=book.image_url,
                url=book.url,
                crawl_timestamp=book.crawl_timestamp
            )
            for book in books
        ]
        
        # Calculate pagination info
        total_pages = (total + per_page - 1) // per_page
        has_next = page < total_pages
        has_prev = page > 1
        
        return BookListResponse(
            books=book_responses,
            total=total,
            page=page,
            per_page=per_page,
            total_pages=total_pages,
            has_next=has_next,
            has_prev=has_prev
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving books: {str(e)}"
        )
    finally:
        await storage.disconnect()


@router.get("/books/{book_id}", response_model=BookResponse)
async def get_book(
    book_id: str,
    api_key: str = Depends(verify_api_key),
    storage: MongoDBStorage = Depends(get_storage)
):
    """Get a specific book by ID (UPC)."""
    try:
        book = await storage.get_book_by_upc(book_id)
        
        if not book:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Book with ID {book_id} not found"
            )
        
        # Convert Book object to BookResponse object
        book_response = BookResponse(
            name=book.name,
            description=book.description,
            category=book.category,
            upc=book.upc,
            price_including_tax=book.price_including_tax,
            price_excluding_tax=book.price_excluding_tax,
            tax_amount=book.tax_amount,
            availability=book.availability,
            availability_count=book.availability_count,
            number_of_reviews=book.number_of_reviews,
            rating=book.rating,
            image_url=book.image_url,
            url=book.url,
            crawl_timestamp=book.crawl_timestamp
        )
        
        return book_response
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving book: {str(e)}"
        )
    finally:
        await storage.disconnect()
