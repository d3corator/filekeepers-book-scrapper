from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import List, Optional

from pymongo import MongoClient
from pymongo.database import Database
from pymongo.errors import DuplicateKeyError

from src.crawler.schemas import Book, ChangeLog, CrawlSession
from src.utils.config import settings

logger = logging.getLogger(__name__)


class MongoDBStorage:
    """MongoDB storage handler for books and crawl sessions"""
    
    def __init__(self):
        self.client: Optional[MongoClient] = None
        self.db: Optional[Database] = None
    
    async def connect(self) -> None:
        """Connect to MongoDB"""
        try:
            self.client = MongoClient(settings.mongodb_uri)
            self.db = self.client[settings.mongodb_database]
            
            # Test connection
            self.client.admin.command('ping')
            logger.info("Connected to MongoDB successfully")
            
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise
    
    async def disconnect(self) -> None:
        """Disconnect from MongoDB"""
        if self.client:
            self.client.close()
            logger.info("Disconnected from MongoDB")
    
    async def store_book(self, book: Book) -> bool:
        """Store a book in the database"""
        try:
            book_dict = book.model_dump()
            
            # Convert Decimal values to float for MongoDB compatibility
            for key, value in book_dict.items():
                if hasattr(value, '__class__') and value.__class__.__name__ == 'Decimal':
                    book_dict[key] = float(value)
            
            # Use upsert to handle duplicates
            result = await asyncio.to_thread(
                self.db.books.replace_one,
                {"url": book.url},
                book_dict,
                upsert=True
            )
            
            if result.upserted_id:
                logger.debug(f"Inserted new book: {book.name}")
                return True
            elif result.modified_count > 0:
                logger.debug(f"Updated existing book: {book.name}")
                return True
            else:
                logger.debug(f"Book unchanged: {book.name}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to store book {book.name}: {e}")
            return False
    
    async def get_book_by_url(self, url: str) -> Optional[Book]:
        """Get a book by its URL"""
        try:
            book_data = await asyncio.to_thread(
                self.db.books.find_one,
                {"url": url}
            )
            if book_data:
                return Book(**book_data)
            return None
        except Exception as e:
            logger.error(f"Failed to get book by URL {url}: {e}")
            return None
    
    async def get_all_books(self, limit: int = 1000) -> List[Book]:
        """Get all books from the database"""
        try:
            books_data = await asyncio.to_thread(
                list,
                self.db.books.find().limit(limit)
            )
            books = [Book(**book_data) for book_data in books_data]
            return books
        except Exception as e:
            logger.error(f"Failed to get all books: {e}")
            return []
    
    async def store_crawl_session(self, session: CrawlSession) -> bool:
        """Store a crawl session"""
        try:
            session_dict = session.model_dump()
            await asyncio.to_thread(
                self.db.crawl_sessions.replace_one,
                {"session_id": session.session_id},
                session_dict,
                upsert=True
            )
            return True
        except Exception as e:
            logger.error(f"Failed to store crawl session {session.session_id}: {e}")
            return False
    
    async def get_latest_crawl_session(self) -> Optional[CrawlSession]:
        """Get the latest crawl session"""
        try:
            session_data = await asyncio.to_thread(
                self.db.crawl_sessions.find_one,
                {},
                sort=[("started_at", -1)]
            )
            if session_data:
                return CrawlSession(**session_data)
            return None
        except Exception as e:
            logger.error(f"Failed to get latest crawl session: {e}")
            return None
    
    async def update_crawl_session(self, session_id: str, updates: dict) -> bool:
        """Update a crawl session"""
        try:
            result = await asyncio.to_thread(
                self.db.crawl_sessions.update_one,
                {"session_id": session_id},
                {"$set": updates}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Failed to update crawl session {session_id}: {e}")
            return False
    
    async def store_change_log(self, change_log: ChangeLog) -> bool:
        """Store a change log entry"""
        try:
            change_dict = change_log.model_dump()
            await asyncio.to_thread(
                self.db.change_logs.insert_one,
                change_dict
            )
            return True
        except Exception as e:
            logger.error(f"Failed to store change log: {e}")
            return False
    
    async def get_change_logs(self, limit: int = 100) -> List[ChangeLog]:
        """Get recent change logs"""
        try:
            logs_data = await asyncio.to_thread(
                list,
                self.db.change_logs.find().sort("timestamp", -1).limit(limit)
            )
            change_logs = [ChangeLog(**log_data) for log_data in logs_data]
            return change_logs
        except Exception as e:
            logger.error(f"Failed to get change logs: {e}")
            return []
    
    async def get_books_count(self) -> int:
        """Get total number of books in the database"""
        try:
            return await asyncio.to_thread(
                self.db.books.count_documents,
                {}
            )
        except Exception as e:
            logger.error(f"Failed to get books count: {e}")
            return 0
    
    async def get_change_logs_by_date_range(
        self, 
        start_date: datetime, 
        end_date: datetime
    ) -> List[ChangeLog]:
        """Get change logs within a date range"""
        try:
            logs_data = await asyncio.to_thread(
                list,
                self.db.change_logs.find({
                    "timestamp": {
                        "$gte": start_date,
                        "$lte": end_date
                    }
                }).sort("timestamp", -1)
            )
            change_logs = [ChangeLog(**log_data) for log_data in logs_data]
            return change_logs
        except Exception as e:
            logger.error(f"Failed to get change logs by date range: {e}")
            return []
    
    async def get_book_by_upc(self, upc: str) -> Optional[Book]:
        """Get a book by its UPC"""
        try:
            book_data = await asyncio.to_thread(
                self.db.books.find_one,
                {"upc": upc}
            )
            if book_data:
                return Book(**book_data)
            return None
        except Exception as e:
            logger.error(f"Failed to get book by UPC {upc}: {e}")
            return None
    
    async def get_books_paginated(
        self, 
        filter_query: dict = None, 
        sort_query: list = None, 
        skip: int = 0, 
        limit: int = 20
    ) -> List[Book]:
        """Get books with pagination and filtering"""
        try:
            if filter_query is None:
                filter_query = {}
            if sort_query is None:
                sort_query = [("name", 1)]
            
            books_data = await asyncio.to_thread(
                list,
                self.db.books.find(filter_query)
                .sort(sort_query)
                .skip(skip)
                .limit(limit)
            )
            books = [Book(**book_data) for book_data in books_data]
            return books
        except Exception as e:
            logger.error(f"Failed to get paginated books: {e}")
            return []
    
    async def get_change_logs_paginated(
        self, 
        filter_query: dict = None, 
        skip: int = 0, 
        limit: int = 20
    ) -> List[ChangeLog]:
        """Get change logs with pagination and filtering"""
        try:
            if filter_query is None:
                filter_query = {}
            
            logs_data = await asyncio.to_thread(
                list,
                self.db.change_logs.find(filter_query)
                .sort("timestamp", -1)
                .skip(skip)
                .limit(limit)
            )
            change_logs = [ChangeLog(**log_data) for log_data in logs_data]
            return change_logs
        except Exception as e:
            logger.error(f"Failed to get paginated change logs: {e}")
            return []
    
    async def get_change_logs_count(self, filter_query: dict = None) -> int:
        """Get count of change logs with filtering"""
        try:
            if filter_query is None:
                filter_query = {}
            
            return await asyncio.to_thread(
                self.db.change_logs.count_documents,
                filter_query
            )
        except Exception as e:
            logger.error(f"Failed to get change logs count: {e}")
            return 0
