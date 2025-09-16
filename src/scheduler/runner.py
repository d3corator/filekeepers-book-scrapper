"""APScheduler runner for automated change detection and crawling."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from src.scheduler.change_detector import ChangeDetector
from src.crawler.crawler import BookCrawler
from src.utils.config import settings

logger = logging.getLogger(__name__)


class SchedulerRunner:
    """APScheduler-based runner for automated jobs."""
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.change_detector = ChangeDetector()
        self.reports_dir = Path("reports")
        self.logs_dir = Path("logs")
        
        # Create directories if they don't exist
        self.reports_dir.mkdir(exist_ok=True)
        self.logs_dir.mkdir(exist_ok=True)
        
    def setup_logging(self) -> None:
        """Setup comprehensive logging for scheduler."""
        # Create logs directory
        self.logs_dir.mkdir(exist_ok=True)
        
        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, settings.log_level.upper()))
        
        # Clear existing handlers
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)
        
        # File handler for general logs
        file_handler = logging.FileHandler(self.logs_dir / "scheduler.log")
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
        
        # File handler for change alerts
        alert_handler = logging.FileHandler(self.logs_dir / "change_alerts.log")
        alert_handler.setLevel(logging.WARNING)
        alert_formatter = logging.Formatter(
            '%(asctime)s - CHANGE ALERT - %(levelname)s - %(message)s'
        )
        alert_handler.setFormatter(alert_formatter)
        root_logger.addHandler(alert_handler)
        
        logger.info("Scheduler logging configured")
    
    def add_jobs(self) -> None:
        """Add scheduled jobs to the scheduler."""
        
        # Daily change detection at 2:00 AM
        self.scheduler.add_job(
            self.daily_change_detection,
            CronTrigger(hour=2, minute=0),
            id="daily_change_detection",
            name="Daily Change Detection",
            max_instances=1,
            replace_existing=True
        )
        
        # Daily report generation at 3:00 AM
        self.scheduler.add_job(
            self.daily_report_generation,
            CronTrigger(hour=3, minute=0),
            id="daily_report_generation",
            name="Daily Report Generation",
            max_instances=1,
            replace_existing=True
        )
        
        # Weekly full crawl on Sunday at 1:00 AM
        self.scheduler.add_job(
            self.weekly_full_crawl,
            CronTrigger(day_of_week=6, hour=1, minute=0),  # Sunday = 6
            id="weekly_full_crawl",
            name="Weekly Full Crawl",
            max_instances=1,
            replace_existing=True
        )
        
        # Health check every hour
        self.scheduler.add_job(
            self.health_check,
            CronTrigger(minute=0),
            id="health_check",
            name="Health Check",
            max_instances=1,
            replace_existing=True
        )
        
        logger.info("Scheduled jobs added to scheduler")
    
    async def daily_change_detection(self) -> None:
        """Run daily change detection."""
        logger.info("Starting daily change detection job")
        
        try:
            changes = await self.change_detector.detect_changes()
            
            if changes["total_changes"] > 0:
                # Log alerts for significant changes
                if changes["new_books"]:
                    logger.warning(f"ALERT: {changes['new_books']} new books detected!")
                
                if changes["removed_books"]:
                    logger.warning(f"ALERT: {changes['removed_books']} books removed!")
                
                if changes["updated_books"]:
                    logger.warning(f"ALERT: {changes['updated_books']} books updated!")
                
                # Log detailed changes
                for change_log in changes["change_logs"]:
                    if change_log.change_type == "new":
                        book_name = change_log.field_changes.get("book", {}).get("new", "Unknown")
                        logger.warning(f"NEW BOOK: {book_name}")
                    elif change_log.change_type == "removed":
                        book_name = change_log.field_changes.get("book", {}).get("old", "Unknown")
                        logger.warning(f"REMOVED BOOK: {book_name}")
                    elif change_log.change_type == "updated":
                        for field_name, changes in change_log.field_changes.items():
                            logger.warning(
                                f"UPDATED BOOK: {change_log.book_id} - "
                                f"{field_name}: {changes['old']} -> {changes['new']}"
                            )
            else:
                logger.info("No changes detected in daily check")
                
        except Exception as e:
            logger.error(f"Error in daily change detection: {e}")
            raise
    
    async def daily_report_generation(self) -> None:
        """Generate daily report."""
        logger.info("Starting daily report generation")
        
        try:
            # Generate report for yesterday
            yesterday = datetime.utcnow().date() - timedelta(days=1)
            report = await self.change_detector.generate_daily_report(yesterday)
            
            # Save report to file
            report_filename = self.reports_dir / f"daily_report_{yesterday.isoformat()}.json"
            with open(report_filename, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            
            logger.info(f"Daily report saved to {report_filename}")
            logger.info(f"Report summary: {report['total_changes']} total changes")
            
        except Exception as e:
            logger.error(f"Error generating daily report: {e}")
            raise
    
    async def weekly_full_crawl(self) -> None:
        """Run weekly full crawl."""
        logger.info("Starting weekly full crawl")
        
        try:
            async with BookCrawler() as crawler:
                session = await crawler.crawl_all_books(resume=False)
                
                logger.info(f"Weekly crawl completed:")
                logger.info(f"  - Books found: {session.total_books_found}")
                logger.info(f"  - Books crawled: {session.books_crawled}")
                logger.info(f"  - Books failed: {session.books_failed}")
                logger.info(f"  - Duration: {session.completed_at - session.started_at}")
                
        except Exception as e:
            logger.error(f"Error in weekly full crawl: {e}")
            raise
    
    async def health_check(self) -> None:
        """Run health check."""
        logger.debug("Running health check")
        
        try:
            # Check database connection
            from src.crawler.storage import MongoDBStorage
            storage = MongoDBStorage()
            await storage.connect()
            
            # Get basic stats
            book_count = await storage.get_books_count()
            latest_session = await storage.get_latest_crawl_session()
            
            await storage.disconnect()
            
            logger.debug(f"Health check passed - Books: {book_count}")
            
            if latest_session:
                days_since_last_crawl = (datetime.utcnow() - latest_session.completed_at).days
                if days_since_last_crawl > 7:
                    logger.warning(f"Last crawl was {days_since_last_crawl} days ago")
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
    
    async def run_manual_change_detection(self) -> None:
        """Run change detection manually."""
        logger.info("Running manual change detection")
        await self.daily_change_detection()
    
    async def run_manual_report(self, date: datetime = None) -> None:
        """Run report generation manually."""
        if date is None:
            date = datetime.utcnow().date()
        
        logger.info(f"Running manual report generation for {date}")
        report = await self.change_detector.generate_daily_report(date)
        
        # Save report to file
        report_filename = self.reports_dir / f"manual_report_{date.isoformat()}.json"
        with open(report_filename, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        logger.info(f"Manual report saved to {report_filename}")
        return report
    
    def start(self) -> None:
        """Start the scheduler."""
        logger.info("Starting scheduler...")
        self.setup_logging()
        self.add_jobs()
        self.scheduler.start()
        logger.info("Scheduler started successfully")
    
    def stop(self) -> None:
        """Stop the scheduler."""
        logger.info("Stopping scheduler...")
        self.scheduler.shutdown()
        logger.info("Scheduler stopped")
    
    async def run_forever(self) -> None:
        """Run the scheduler forever."""
        self.start()
        
        try:
            # Keep the scheduler running
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        finally:
            self.stop()
