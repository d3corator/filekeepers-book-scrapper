"""Change detection logic for monitoring book data changes."""

from __future__ import annotations

import asyncio
import hashlib
import logging
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple

import httpx

from src.crawler.crawler import BookCrawler
from src.crawler.schemas import Book, ChangeLog
from src.crawler.storage import MongoDBStorage
from src.utils.config import settings

logger = logging.getLogger(__name__)


class ChangeDetector:
    """Detects changes in book data by comparing current vs stored data."""
    
    def __init__(self):
        self.storage = MongoDBStorage()
        self.crawler = BookCrawler()
        
    async def detect_changes(self) -> Dict[str, any]:
        """Detect changes by crawling current data and comparing with stored data."""
        logger.info("Starting change detection process")
        
        try:
            # Connect to storage
            await self.storage.connect()
            
            # Get current book data from website
            logger.info("Crawling current book data...")
            current_books = await self._get_current_books()
            logger.info(f"Found {len(current_books)} books on website")
            
            # Get stored book data from database
            logger.info("Retrieving stored book data...")
            stored_books = await self._get_stored_books()
            logger.info(f"Found {len(stored_books)} books in database")
            
            # Compare and detect changes
            changes = await self._compare_books(current_books, stored_books)
            
            # Store change logs
            if changes["total_changes"] > 0:
                await self._store_change_logs(changes["change_logs"])
                logger.info(f"Detected {changes['total_changes']} changes")
            else:
                logger.info("No changes detected")
            
            return changes
            
        except Exception as e:
            logger.error(f"Error during change detection: {e}")
            raise
        finally:
            await self.storage.disconnect()
    
    async def _get_current_books(self) -> Dict[str, Book]:
        """Get current book data from the website."""
        current_books = {}
        
        try:
            # Get all book URLs
            book_urls = await self.crawler._get_all_book_urls()
            logger.info(f"Found {len(book_urls)} book URLs to check")
            
            # Crawl each book (with limited concurrency for change detection)
            semaphore = asyncio.Semaphore(5)  # Lower concurrency for change detection
            
            async def crawl_book(url: str) -> Optional[Book]:
                async with semaphore:
                    try:
                        async with httpx.AsyncClient(timeout=settings.request_timeout) as client:
                            response = await client.get(url)
                            response.raise_for_status()
                            
                            book = await self.crawler._parse_book_page(url, response.text)
                            if book:
                                logger.debug(f"Crawled: {book.name}")
                            return book
                    except Exception as e:
                        logger.warning(f"Failed to crawl {url}: {e}")
                        return None
            
            # Crawl all books concurrently
            tasks = [crawl_book(url) for url in book_urls]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for result in results:
                if isinstance(result, Book):
                    current_books[result.url] = result
                elif isinstance(result, Exception):
                    logger.warning(f"Exception during crawling: {result}")
            
            logger.info(f"Successfully crawled {len(current_books)} books")
            return current_books
            
        except Exception as e:
            logger.error(f"Error getting current books: {e}")
            raise
    
    async def _get_stored_books(self) -> Dict[str, Book]:
        """Get stored book data from the database."""
        try:
            books = await self.storage.get_all_books(limit=10000)  # Get all books
            return {book.url: book for book in books}
        except Exception as e:
            logger.error(f"Error getting stored books: {e}")
            raise
    
    async def _compare_books(
        self, 
        current_books: Dict[str, Book], 
        stored_books: Dict[str, Book]
    ) -> Dict[str, any]:
        """Compare current and stored books to detect changes."""
        changes = {
            "new_books": [],
            "removed_books": [],
            "updated_books": [],
            "change_logs": [],
            "total_changes": 0
        }
        
        current_urls = set(current_books.keys())
        stored_urls = set(stored_books.keys())
        
        # Find new books (in current but not in stored)
        new_urls = current_urls - stored_urls
        for url in new_urls:
            book = current_books[url]
            changes["new_books"].append(book)
            changes["change_logs"].append(
                ChangeLog(
                    book_id=book.upc,  # Use UPC as book ID
                    change_type="new",
                    field_changes={"book": {"old": None, "new": book.name}},
                    timestamp=datetime.utcnow()
                )
            )
            logger.info(f"NEW BOOK: {book.name}")
        
        # Find removed books (in stored but not in current)
        removed_urls = stored_urls - current_urls
        for url in removed_urls:
            book = stored_books[url]
            changes["removed_books"].append(book)
            changes["change_logs"].append(
                ChangeLog(
                    book_id=book.upc,  # Use UPC as book ID
                    change_type="removed",
                    field_changes={"book": {"old": book.name, "new": None}},
                    timestamp=datetime.utcnow()
                )
            )
            logger.warning(f"REMOVED BOOK: {book.name}")
        
        # Find updated books (in both but with different content)
        common_urls = current_urls & stored_urls
        for url in common_urls:
            current_book = current_books[url]
            stored_book = stored_books[url]
            
            # Compare content hashes for efficiency
            if current_book.content_hash != stored_book.content_hash:
                field_changes = self._compare_book_fields(current_book, stored_book)
                if field_changes:
                    changes["updated_books"].append({
                        "book": current_book,
                        "changes": field_changes
                    })
                    
                    # Create change logs for each field change
                    field_changes_dict = {}
                    for field_name, (old_value, new_value) in field_changes.items():
                        field_changes_dict[field_name] = {
                            "old": str(old_value) if old_value is not None else None,
                            "new": str(new_value) if new_value is not None else None
                        }
                    
                    changes["change_logs"].append(
                        ChangeLog(
                            book_id=current_book.upc,  # Use UPC as book ID
                            change_type="updated",
                            field_changes=field_changes_dict,
                            timestamp=datetime.utcnow()
                        )
                    )
                    
                    logger.info(f"UPDATED BOOK: {current_book.name} - {len(field_changes)} changes")
        
        changes["total_changes"] = len(changes["change_logs"])
        return changes
    
    def _compare_book_fields(self, current: Book, stored: Book) -> Dict[str, Tuple[any, any]]:
        """Compare individual fields between current and stored books."""
        changes = {}
        
        # Fields to compare (excluding metadata fields)
        fields_to_compare = [
            "name", "description", "category", "upc",
            "price_including_tax", "price_excluding_tax", "tax_amount",
            "availability", "availability_count", "number_of_reviews", "rating"
        ]
        
        for field in fields_to_compare:
            current_value = getattr(current, field)
            stored_value = getattr(stored, field)
            
            if current_value != stored_value:
                changes[field] = (stored_value, current_value)
        
        return changes
    
    async def _store_change_logs(self, change_logs: List[ChangeLog]) -> None:
        """Store change logs in the database."""
        try:
            for change_log in change_logs:
                await self.storage.store_change_log(change_log)
            logger.info(f"Stored {len(change_logs)} change logs")
        except Exception as e:
            logger.error(f"Error storing change logs: {e}")
            raise
    
    async def generate_daily_report(self, date: Optional[datetime] = None) -> Dict[str, any]:
        """Generate a daily report of changes."""
        if date is None:
            date = datetime.utcnow().date()
        
        logger.info(f"Generating daily report for {date}")
        
        try:
            await self.storage.connect()
            
            # Get change logs for the specified date
            start_datetime = datetime.combine(date, datetime.min.time())
            end_datetime = datetime.combine(date, datetime.max.time())
            
            change_logs = await self.storage.get_change_logs_by_date_range(
                start_datetime, end_datetime
            )
            
            # Generate report
            report = {
                "date": date.isoformat(),
                "total_changes": len(change_logs),
                "new_books": 0,
                "removed_books": 0,
                "updated_books": 0,
                "price_changes": 0,
                "availability_changes": 0,
                "changes_by_type": {},
                "changes_by_category": {},
                "top_changed_books": []
            }
            
            # Analyze changes
            book_change_counts = {}
            for change_log in change_logs:
                # Count by type
                change_type = change_log.change_type
                report["changes_by_type"][change_type] = report["changes_by_type"].get(change_type, 0) + 1
                
                if change_type == "new":
                    report["new_books"] += 1
                elif change_type == "removed":
                    report["removed_books"] += 1
                elif change_type == "updated":
                    report["updated_books"] += 1
                    
                    # Track specific field changes
                    for field_name in change_log.field_changes.keys():
                        if "price" in field_name:
                            report["price_changes"] += 1
                        if "availability" in field_name:
                            report["availability_changes"] += 1
                
                # Count changes per book
                book_change_counts[change_log.book_id] = book_change_counts.get(change_log.book_id, 0) + 1
            
            # Get top changed books
            sorted_books = sorted(book_change_counts.items(), key=lambda x: x[1], reverse=True)
            report["top_changed_books"] = [
                {"book_id": book_id, "change_count": count} 
                for book_id, count in sorted_books[:10]
            ]
            
            logger.info(f"Generated report: {report['total_changes']} total changes")
            return report
            
        except Exception as e:
            logger.error(f"Error generating daily report: {e}")
            raise
        finally:
            await self.storage.disconnect()
