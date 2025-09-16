"""Tests for scheduler runner."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime
from pathlib import Path

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.scheduler.runner import SchedulerRunner


def test_runner_initialization():
    """Test scheduler runner initialization."""
    runner = SchedulerRunner()
    assert runner.scheduler is not None
    assert runner.change_detector is not None
    assert runner.reports_dir == Path("reports")
    assert runner.logs_dir == Path("logs")


def test_setup_logging():
    """Test logging setup."""
    runner = SchedulerRunner()
    runner.setup_logging()
    
    # Check that directories were created
    assert runner.reports_dir.exists()
    assert runner.logs_dir.exists()


def test_add_jobs():
    """Test adding jobs to scheduler."""
    runner = SchedulerRunner()
    runner.add_jobs()
    
    # Check that jobs were added
    jobs = runner.scheduler.get_jobs()
    job_ids = [job.id for job in jobs]
    
    assert "daily_change_detection" in job_ids
    assert "daily_report_generation" in job_ids
    assert "weekly_full_crawl" in job_ids
    assert "health_check" in job_ids


@pytest.mark.asyncio
async def test_daily_change_detection():
    """Test daily change detection job."""
    runner = SchedulerRunner()
    
    # Mock change detector
    with patch.object(runner.change_detector, 'detect_changes', new_callable=AsyncMock) as mock_detect:
        mock_detect.return_value = {
            "total_changes": 2,
            "new_books": 1,
            "removed_books": 0,
            "updated_books": 1,
            "change_logs": [
                MagicMock(change_type="new", new_value="New Book"),
                MagicMock(change_type="updated", book_url="http://example.com/book", field_name="price", old_value="10.00", new_value="12.00")
            ]
        }
        
        await runner.daily_change_detection()
        
        # Verify that detect_changes was called
        mock_detect.assert_called_once()


@pytest.mark.asyncio
async def test_daily_report_generation():
    """Test daily report generation job."""
    runner = SchedulerRunner()
    
    # Mock change detector
    with patch.object(runner.change_detector, 'generate_daily_report', new_callable=AsyncMock) as mock_report:
        mock_report.return_value = {
            "date": "2024-01-01",
            "total_changes": 5,
            "new_books": 2,
            "removed_books": 1,
            "updated_books": 2
        }
        
        # Mock file operations
        with patch('builtins.open', MagicMock()) as mock_open:
            await runner.daily_report_generation()
            
            # Verify that generate_daily_report was called
            mock_report.assert_called_once()
            
            # Verify that file was opened for writing
            mock_open.assert_called_once()


@pytest.mark.asyncio
async def test_weekly_full_crawl():
    """Test weekly full crawl job."""
    runner = SchedulerRunner()
    
    # Mock BookCrawler
    with patch('src.scheduler.runner.BookCrawler') as mock_crawler_class:
        mock_crawler = AsyncMock()
        mock_crawler_class.return_value.__aenter__.return_value = mock_crawler
        
        # Mock crawl session
        mock_session = MagicMock()
        mock_session.total_books_found = 1000
        mock_session.books_crawled = 995
        mock_session.books_failed = 5
        mock_session.completed_at = datetime.utcnow()
        mock_session.started_at = datetime.utcnow()
        
        mock_crawler.crawl_all_books.return_value = mock_session
        
        await runner.weekly_full_crawl()
        
        # Verify that crawl_all_books was called
        mock_crawler.crawl_all_books.assert_called_once_with(resume=False)


@pytest.mark.asyncio
async def test_health_check():
    """Test health check job."""
    runner = SchedulerRunner()
    
    # Mock storage
    with patch('src.crawler.storage.MongoDBStorage') as mock_storage_class:
        mock_storage = AsyncMock()
        mock_storage_class.return_value = mock_storage
        
        mock_storage.get_books_count.return_value = 1000
        mock_storage.get_latest_crawl_session.return_value = MagicMock(
            completed_at=datetime.utcnow()
        )
        
        await runner.health_check()
        
        # Verify that storage methods were called
        mock_storage.connect.assert_called_once()
        mock_storage.get_books_count.assert_called_once()
        mock_storage.get_latest_crawl_session.assert_called_once()
        mock_storage.disconnect.assert_called_once()


@pytest.mark.asyncio
async def test_manual_change_detection():
    """Test manual change detection."""
    runner = SchedulerRunner()
    
    with patch.object(runner, 'daily_change_detection', new_callable=AsyncMock) as mock_daily:
        await runner.run_manual_change_detection()
        mock_daily.assert_called_once()


@pytest.mark.asyncio
async def test_manual_report():
    """Test manual report generation."""
    runner = SchedulerRunner()
    
    with patch.object(runner.change_detector, 'generate_daily_report', new_callable=AsyncMock) as mock_report:
        mock_report.return_value = {"date": "2024-01-01", "total_changes": 0}
        
        with patch('builtins.open', MagicMock()):
            report = await runner.run_manual_report()
            
            mock_report.assert_called_once()
            assert report is not None
