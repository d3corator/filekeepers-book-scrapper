from __future__ import annotations

import asyncio
import logging
import re
import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Set
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from src.crawler.schemas import Book, CrawlSession
from src.crawler.storage import MongoDBStorage
from src.utils.config import settings

logger = logging.getLogger(__name__)


class BookCrawler:
    """Async crawler for books.toscrape.com"""
    
    def __init__(self):
        self.storage = MongoDBStorage()
        self.session_id = str(uuid.uuid4())
        self.crawled_urls: Set[str] = set()
        self.failed_urls: Set[str] = set()
        self.semaphore = asyncio.Semaphore(settings.max_concurrent_requests)
        
    async def __aenter__(self):
        await self.storage.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.storage.disconnect()
    
    async def crawl_all_books(self, resume: bool = False) -> CrawlSession:
        """Crawl all books from the website"""
        logger.info(f"Starting crawl session {self.session_id}")
        
        # Create or resume crawl session
        if resume:
            latest_session = await self.storage.get_latest_crawl_session()
            if latest_session and latest_session.status == "running":
                self.session_id = latest_session.session_id
                logger.info(f"Resuming session {self.session_id}")
            else:
                logger.info("No running session found, starting fresh")
        
        session = CrawlSession(
            session_id=self.session_id,
            started_at=datetime.utcnow(),
            status="running"
        )
        await self.storage.store_crawl_session(session)
        
        try:
            # Get all book URLs
            book_urls = await self._get_all_book_urls()
            session.total_books_found = len(book_urls)
            logger.info(f"Found {len(book_urls)} books to crawl")
            
            # Log first few URLs for debugging
            if book_urls:
                logger.info(f"Sample URLs: {book_urls[:3]}")
            
            # Crawl books concurrently
            tasks = []
            for url in book_urls:
                task = asyncio.create_task(self._crawl_single_book(url))
                tasks.append(task)
            
            # Process results
            for task in asyncio.as_completed(tasks):
                try:
                    success = await task
                    if success:
                        session.books_crawled += 1
                    else:
                        session.books_failed += 1
                except Exception as e:
                    logger.error(f"Task failed: {e}")
                    session.books_failed += 1
                
                # Update session progress
                await self.storage.update_crawl_session(
                    self.session_id,
                    {
                        "books_crawled": session.books_crawled,
                        "books_failed": session.books_failed
                    }
                )
            
            # Mark session as completed
            session.status = "completed"
            session.completed_at = datetime.utcnow()
            await self.storage.store_crawl_session(session)
            
            logger.info(f"Crawl completed. Crawled: {session.books_crawled}, Failed: {session.books_failed}")
            return session
            
        except Exception as e:
            logger.error(f"Crawl failed: {e}")
            session.status = "failed"
            session.error_message = str(e)
            session.completed_at = datetime.utcnow()
            await self.storage.store_crawl_session(session)
            raise
    
    async def _get_all_book_urls(self) -> List[str]:
        """Get all book URLs from the website"""
        book_urls = []
        page = 1
        
        async with httpx.AsyncClient(timeout=settings.request_timeout) as client:
            while True:
                try:
                    # Get main catalog pages
                    catalog_url = f"{settings.base_url}/catalogue/page-{page}.html"
                    response = await client.get(catalog_url)
                    
                    if response.status_code == 404:
                        break  # No more pages
                    
                    response.raise_for_status()
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Find book links
                    book_links = soup.find_all('h3')
                    for link in book_links:
                        book_link = link.find('a')
                        if book_link and book_link.get('href'):
                            book_url = self._construct_book_url(book_link['href'])
                            if book_url:
                                book_urls.append(book_url)
                    
                    if not book_links:
                        break  # No more books on this page
                    
                    page += 1
                    await asyncio.sleep(settings.rate_limit_delay)
                    
                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 404:
                        break
                    logger.warning(f"HTTP error on page {page}: {e}")
                    break
                except Exception as e:
                    logger.error(f"Error getting book URLs from page {page}: {e}")
                    break
        
        return list(set(book_urls))  # Remove duplicates
    
    async def _get_category_urls(self, client: httpx.AsyncClient) -> List[str]:
        """Get all category URLs"""
        try:
            response = await client.get(settings.base_url)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            category_links = soup.find('ul', class_='nav-list').find_all('a')
            category_urls = []
            
            for link in category_links:
                href = link.get('href')
                if href:
                    category_url = urljoin(settings.base_url, href)
                    category_urls.append(category_url)
            
            return category_urls
        except Exception as e:
            logger.error(f"Failed to get category URLs: {e}")
            return []
    
    async def _get_books_from_category(self, client: httpx.AsyncClient, category_url: str) -> List[str]:
        """Get all book URLs from a category"""
        book_urls = []
        page = 1
        
        try:
            while True:
                if page == 1:
                    url = category_url
                else:
                    # Handle pagination in category pages
                    base_url = category_url.replace('/index.html', '')
                    url = f"{base_url}/page-{page}.html"
                
                response = await client.get(url)
                
                if response.status_code == 404:
                    break
                
                response.raise_for_status()
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Find book links
                book_links = soup.find_all('h3')
                for link in book_links:
                    book_link = link.find('a')
                    if book_link and book_link.get('href'):
                        book_url = self._construct_book_url(book_link['href'])
                        if book_url:
                            book_urls.append(book_url)
                
                if not book_links:
                    break
                
                page += 1
                await asyncio.sleep(settings.rate_limit_delay)
                
        except Exception as e:
            logger.error(f"Failed to get books from category {category_url}: {e}")
        
        return book_urls
    
    async def _crawl_single_book(self, url: str) -> bool:
        """Crawl a single book page"""
        async with self.semaphore:
            for attempt in range(settings.retry_attempts):
                try:
                    async with httpx.AsyncClient(timeout=settings.request_timeout) as client:
                        response = await client.get(url)
                        response.raise_for_status()
                        
                        # Parse book data
                        book = await self._parse_book_page(url, response.text)
                        if book:
                            # Store in database
                            success = await self.storage.store_book(book)
                            if success:
                                self.crawled_urls.add(url)
                                logger.debug(f"Successfully crawled: {book.name}")
                                return True
                            else:
                                logger.warning(f"Failed to store book: {book.name}")
                                return False
                        else:
                            logger.warning(f"Failed to parse book from: {url}")
                            return False
                
                except httpx.HTTPStatusError as e:
                    logger.warning(f"HTTP error for {url} (attempt {attempt + 1}): {e}")
                    if e.response.status_code == 404:
                        logger.error(f"404 Not Found for URL: {url}")
                    if attempt == settings.retry_attempts - 1:
                        self.failed_urls.add(url)
                        return False
                
                except Exception as e:
                    logger.error(f"Error crawling {url} (attempt {attempt + 1}): {e}")
                    if attempt == settings.retry_attempts - 1:
                        self.failed_urls.add(url)
                        return False
                
                # Wait before retry
                if attempt < settings.retry_attempts - 1:
                    await asyncio.sleep(settings.retry_delay * (attempt + 1))
            
            return False
    
    async def _parse_book_page(self, url: str, html: str) -> Optional[Book]:
        """Parse book data from HTML"""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Extract book information
            name = self._extract_text(soup, 'h1')
            description = self._extract_text(soup, '#product_description + p')
            
            # UPC (Universal Product Code)
            upc = self._extract_text(soup, 'table.table tr:nth-of-type(1) td:nth-of-type(2)')
            
            # Category (from breadcrumb)
            category = "Unknown"
            breadcrumb = soup.find('ul', class_='breadcrumb')
            if breadcrumb:
                category_links = breadcrumb.find_all('a')
                if len(category_links) >= 2:
                    category = category_links[1].get_text().strip()
            
            # Price information
            price_including_tax = self._extract_price(soup, 'p.price_color')
            price_excluding_tax = self._extract_price(soup, 'table.table tr:nth-of-type(2) td:nth-of-type(2)')
            tax_amount = price_including_tax - price_excluding_tax
            
            # Availability
            availability = self._extract_text(soup, 'p.availability')
            availability_count = self._extract_availability_count(availability)
            
            # Number of reviews
            reviews_text = self._extract_text(soup, 'table.table tr:nth-of-type(3) td:nth-of-type(2)')
            number_of_reviews = 0
            if reviews_text and reviews_text.isdigit():
                number_of_reviews = int(reviews_text)
            
            # Image URL
            image_element = soup.find('div', class_='item active').find('img')
            image_url = ""
            if image_element and image_element.get('src'):
                image_url = urljoin(settings.base_url, image_element['src'])
            
            # Rating
            rating = 0
            rating_element = soup.find('p', class_='star-rating')
            if rating_element:
                rating_classes = rating_element.get('class', [])
                for cls in rating_classes:
                    if cls.startswith('One'):
                        rating = 1
                    elif cls.startswith('Two'):
                        rating = 2
                    elif cls.startswith('Three'):
                        rating = 3
                    elif cls.startswith('Four'):
                        rating = 4
                    elif cls.startswith('Five'):
                        rating = 5
            
            # Create book object
            book = Book(
                name=name,
                description=description,
                category=category,
                upc=upc,
                price_including_tax=price_including_tax,
                price_excluding_tax=price_excluding_tax,
                tax_amount=tax_amount,
                availability=availability,
                availability_count=availability_count,
                number_of_reviews=number_of_reviews,
                image_url=image_url,
                rating=rating,
                url=url,
                raw_html=html if settings.store_raw_html else None
            )
            
            return book
            
        except Exception as e:
            logger.error(f"Failed to parse book page {url}: {e}")
            return None
    
    def _extract_text(self, soup: BeautifulSoup, selector: str) -> str:
        """Extract text from a CSS selector"""
        try:
            element = soup.select_one(selector)
            return element.get_text().strip() if element else ""
        except Exception:
            return ""
    
    def _extract_price(self, soup: BeautifulSoup, selector: str) -> Decimal:
        """Extract price from a CSS selector"""
        try:
            element = soup.select_one(selector)
            if element:
                price_text = element.get_text().strip()
                # Remove currency symbols and convert to Decimal
                price_text = re.sub(r'[^\d.,]', '', price_text)
                if price_text:
                    return Decimal(price_text)
            return Decimal('0.00')
        except Exception:
            return Decimal('0.00')
    
    def _extract_availability_count(self, availability_text: str) -> int:
        """Extract availability count from availability text"""
        try:
            # Look for patterns like "In stock (22 available)" or "Out of stock"
            if "In stock" in availability_text:
                # Extract number from parentheses
                match = re.search(r'\((\d+)\s+available\)', availability_text)
                if match:
                    return int(match.group(1))
                return 1  # Default to 1 if "In stock" but no count
            return 0  # Out of stock or no stock
        except Exception:
            return 0
    
    def _construct_book_url(self, href: str) -> Optional[str]:
        """Construct proper book URL from href"""
        try:
            # Handle different href formats
            if href.startswith('http'):
                return href  # Already absolute URL
            
            # Handle relative URLs
            if href.startswith('/'):
                # Absolute path from root
                constructed_url = f"{settings.base_url}{href}"
            elif href.startswith('../'):
                # Relative path going up directories
                # Remove '../' and construct proper path
                clean_href = href.replace('../', '')
                constructed_url = f"{settings.base_url}/{clean_href}"
            else:
                # Relative path from current directory
                # For books.toscrape.com, most book URLs are in /catalogue/
                if not href.startswith('catalogue/'):
                    href = f"catalogue/{href}"
                constructed_url = f"{settings.base_url}/{href}"
            
            logger.debug(f"Constructed URL: {href} -> {constructed_url}")
            return constructed_url
                
        except Exception as e:
            logger.error(f"Failed to construct book URL from {href}: {e}")
            return None
