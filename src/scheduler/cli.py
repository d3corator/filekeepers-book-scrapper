"""Command-line interface for the scheduler."""

import argparse
import asyncio
import logging
import sys
from datetime import datetime

from src.scheduler.runner import SchedulerRunner

logger = logging.getLogger(__name__)


def setup_logging() -> None:
    """Setup logging for CLI."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('scheduler.log')
        ]
    )


async def run_scheduler() -> None:
    """Run the scheduler daemon."""
    logger.info("Starting scheduler daemon...")
    
    try:
        runner = SchedulerRunner()
        await runner.run_forever()
    except Exception as e:
        logger.error(f"Scheduler failed: {e}")
        sys.exit(1)


async def run_change_detection() -> None:
    """Run change detection manually."""
    logger.info("Running manual change detection...")
    
    try:
        runner = SchedulerRunner()
        runner.setup_logging()
        await runner.run_manual_change_detection()
        logger.info("Change detection completed successfully")
    except Exception as e:
        logger.error(f"Change detection failed: {e}")
        sys.exit(1)


async def run_report(date_str: str = None) -> None:
    """Run report generation manually."""
    logger.info("Running manual report generation...")
    
    try:
        runner = SchedulerRunner()
        runner.setup_logging()
        
        if date_str:
            date = datetime.strptime(date_str, "%Y-%m-%d").date()
        else:
            date = None
            
        report = await runner.run_manual_report(date)
        
        # Print report summary
        print(f"\nReport Summary:")
        print(f"Date: {report['date']}")
        print(f"Total Changes: {report['total_changes']}")
        print(f"New Books: {report['new_books']}")
        print(f"Removed Books: {report['removed_books']}")
        print(f"Updated Books: {report['updated_books']}")
        print(f"Price Changes: {report['price_changes']}")
        print(f"Availability Changes: {report['availability_changes']}")
        
        if report['top_changed_books']:
            print(f"\nTop Changed Books:")
            for book in report['top_changed_books'][:5]:
                print(f"  - {book['url']}: {book['change_count']} changes")
        
        logger.info("Report generation completed successfully")
        
    except Exception as e:
        logger.error(f"Report generation failed: {e}")
        sys.exit(1)


def main() -> None:
    """Main CLI entry point."""
    setup_logging()
    
    parser = argparse.ArgumentParser(prog="scheduler", description="Book scraper scheduler")
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # Run scheduler daemon
    run_parser = subparsers.add_parser("run", help="Run the scheduler daemon")
    
    # Run change detection manually
    detect_parser = subparsers.add_parser("detect", help="Run change detection manually")
    
    # Generate report manually
    report_parser = subparsers.add_parser("report", help="Generate daily report")
    report_parser.add_argument(
        "--date", 
        help="Date for report (YYYY-MM-DD format, defaults to today)"
    )
    
    args = parser.parse_args()
    
    if args.command == "run":
        asyncio.run(run_scheduler())
    elif args.command == "detect":
        asyncio.run(run_change_detection())
    elif args.command == "report":
        asyncio.run(run_report(args.date))


if __name__ == "__main__":
    main()
