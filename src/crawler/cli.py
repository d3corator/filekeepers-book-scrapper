import argparse
import asyncio
import logging
import sys
from datetime import datetime

from src.crawler.crawler import BookCrawler
from src.utils.config import settings


def setup_logging() -> None:
    """Setup logging configuration"""
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('crawler.log')
        ]
    )


async def crawl(resume: bool) -> None:
    """Run the book crawler"""
    logger = logging.getLogger(__name__)
    
    try:
        async with BookCrawler() as crawler:
            logger.info(f"Starting crawler (resume={resume})")
            session = await crawler.crawl_all_books(resume=resume)
            
            logger.info(f"Crawl completed successfully!")
            logger.info(f"Session ID: {session.session_id}")
            logger.info(f"Books found: {session.total_books_found}")
            logger.info(f"Books crawled: {session.books_crawled}")
            logger.info(f"Books failed: {session.books_failed}")
            logger.info(f"Duration: {session.completed_at - session.started_at}")
            
    except Exception as e:
        logger.error(f"Crawler failed: {e}")
        sys.exit(1)


def main() -> None:
    """Main CLI entry point"""
    setup_logging()
    
    parser = argparse.ArgumentParser(prog="crawler")
    sub = parser.add_subparsers(dest="command", required=True)

    p_crawl = sub.add_parser("crawl", help="Run the book crawler")
    p_crawl.add_argument("--resume", action="store_true", help="Resume last successful crawl")

    args = parser.parse_args()

    if args.command == "crawl":
        asyncio.run(crawl(resume=args.resume))


if __name__ == "__main__":
    main()

