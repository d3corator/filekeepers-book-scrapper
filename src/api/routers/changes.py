"""Change-related API endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.api.auth import verify_api_key
from src.api.schemas import ChangeListResponse, ChangeLogResponse
from src.crawler.storage import MongoDBStorage

router = APIRouter()


async def get_storage() -> MongoDBStorage:
    """Get MongoDB storage instance."""
    storage = MongoDBStorage()
    await storage.connect()
    return storage


@router.get("/changes", response_model=ChangeListResponse)
async def get_changes(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    change_type: Optional[str] = Query(None, description="Filter by change type"),
    book_id: Optional[str] = Query(None, description="Filter by book ID"),
    api_key: str = Depends(verify_api_key),
    storage: MongoDBStorage = Depends(get_storage)
):
    """Get recent changes with filtering and pagination."""
    try:
        # Build filter query
        filter_query = {}
        
        if change_type:
            filter_query["change_type"] = change_type
        
        if book_id:
            filter_query["book_id"] = book_id
        
        # Calculate pagination
        skip = (page - 1) * per_page
        
        # Get total count
        total = await storage.get_change_logs_count(filter_query)
        
        # Get changes with pagination
        changes = await storage.get_change_logs_paginated(
            filter_query=filter_query,
            skip=skip,
            limit=per_page
        )
        
        # Convert ChangeLog objects to ChangeLogResponse objects
        change_responses = [
            ChangeLogResponse(
                book_id=change.book_id,
                change_type=change.change_type,
                field_changes=change.field_changes,
                timestamp=change.timestamp,
                session_id=change.session_id
            )
            for change in changes
        ]
        
        # Calculate pagination info
        total_pages = (total + per_page - 1) // per_page
        has_next = page < total_pages
        has_prev = page > 1
        
        return ChangeListResponse(
            changes=change_responses,
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
            detail=f"Error retrieving changes: {str(e)}"
        )
    finally:
        await storage.disconnect()
