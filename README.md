# Book Scraper

A scalable and fault-tolerant web crawling solution with automated change detection and scheduling for https://books.toscrape.com.

## Features

- **Async Web Crawling**: High-performance async crawling using httpx
- **MongoDB Storage**: NoSQL database with proper indexing and schema
- **Retry Logic**: Robust error handling with configurable retry attempts
- **Resume Functionality**: Resume from last successful crawl in case of failure
- **Change Detection**: Automated detection of new, updated, and removed books
- **Scheduled Monitoring**: Daily change detection and weekly full crawls
- **Comprehensive Logging**: Detailed logging with change alerts and reports
- **Daily Reports**: JSON reports of daily changes and statistics

## Project Structure

```
src/
├── crawler/          # Web crawling logic
│   ├── cli.py       # Command-line interface
│   ├── crawler.py   # Main crawler implementation
│   ├── schemas.py   # Pydantic data models
│   └── storage.py   # MongoDB storage handler
├── scheduler/        # Change detection and scheduling
│   ├── cli.py       # Scheduler command-line interface
│   ├── change_detector.py  # Change detection logic
│   └── runner.py    # APScheduler runner
└── utils/           # Configuration and utilities
```

## Prerequisites

- Python 3.11+
- Docker and Docker Compose
- PDM (Python Dependency Manager)

## Setup Instructions

### 1. Install PDM

```bash
pipx install pdm
# or
pip install --user pdm
```

### 2. Clone and Setup Project

```bash
git clone <repository-url>
cd book-scraper

# Create virtual environment
pdm venv create -f 3.11
pdm use -f $(pdm venv list --path | tail -1)

# Install dependencies
pdm install -G :all
```

### 3. Start MongoDB

```bash
# Start MongoDB and Mongo Express
docker-compose up -d

# MongoDB will be available at localhost:27017
# Mongo Express (web UI) will be available at http://localhost:8081
# Username: admin, Password: admin
```

### 4. Configure Environment

```bash
# Copy example environment file
cp env.example .env

# Edit .env file with your configuration
```

## Usage

### Run the Crawler

```bash
# Start fresh crawl
pdm run crawl

# Resume from last checkpoint
pdm run crawl --resume
```

### Run the Scheduler

```bash
# Start the scheduler daemon (runs continuously)
pdm run scheduler

# Run change detection manually
pdm run detect

# Generate daily report
pdm run report

# Generate report for specific date
pdm run report --date 2024-01-15
```


### Run Tests

```bash
pdm run test
```

### Code Quality

```bash
# Lint code
pdm run lint

# Format code
pdm run format

# Type check
pdm run typecheck
```

## Configuration

The application can be configured via environment variables or `.env` file:

| Variable | Default | Description |
|----------|---------|-------------|
| `MONGODB_URI` | `mongodb://admin:password@localhost:27017/book_scraper?authSource=admin` | MongoDB connection string |
| `MONGODB_DATABASE` | `book_scraper` | Database name |
| `BASE_URL` | `https://books.toscrape.com` | Target website URL |
| `MAX_CONCURRENT_REQUESTS` | `10` | Maximum concurrent HTTP requests |
| `REQUEST_TIMEOUT` | `30` | HTTP request timeout in seconds |
| `RETRY_ATTEMPTS` | `3` | Number of retry attempts for failed requests |
| `RETRY_DELAY` | `1.0` | Delay between retries in seconds |
| `RATE_LIMIT_DELAY` | `0.1` | Delay between requests in seconds |
| `STORE_RAW_HTML` | `true` | Whether to store raw HTML snapshots |
| `LOG_LEVEL` | `INFO` | Logging level |

## Data Schema

### Book Document

```json
{
  "_id": "ObjectId",
  "name": "Book Title",
  "description": "Book description...",
  "category": "Fiction",
  "upc": "123456789",
  "price_including_tax": "19.99",
  "price_excluding_tax": "16.66",
  "tax_amount": "3.33",
  "availability": "In stock (22 available)",
  "availability_count": 22,
  "number_of_reviews": 0,
  "image_url": "https://books.toscrape.com/media/cache/...",
  "rating": 3,
  "url": "https://books.toscrape.com/catalogue/...",
  "crawl_timestamp": "2024-01-01T12:00:00Z",
  "status": "crawled",
  "raw_html": "<html>...</html>",
  "content_hash": "md5hash"
}
```

### Crawl Session Document

```json
{
  "_id": "ObjectId",
  "session_id": "uuid",
  "started_at": "2024-01-01T12:00:00Z",
  "completed_at": "2024-01-01T12:30:00Z",
  "status": "completed",
  "total_books_found": 1000,
  "books_crawled": 995,
  "books_failed": 5,
  "last_crawled_url": "https://books.toscrape.com/catalogue/...",
  "error_message": null
}
```


## Development

### Adding New Features

1. Create feature branch
2. Implement changes with tests
3. Run quality checks: `pdm run lint && pdm run typecheck && pdm run test`
4. Create pull request

### Testing

```bash
# Run all tests
pdm run test

# Run with coverage
pdm run test --cov=src --cov-report=html

# Run specific test file
pdm run pytest tests/crawler/test_crawler.py
```

## Scheduler Features

### Automated Jobs
- **Daily Change Detection** (2:00 AM): Detects new, updated, and removed books
- **Daily Report Generation** (3:00 AM): Creates JSON reports of daily changes
- **Weekly Full Crawl** (Sunday 1:00 AM): Performs complete site crawl
- **Health Checks** (Every hour): Monitors system health

### Change Detection
- **Content Hash Comparison**: Efficient change detection using MD5 hashes
- **Detailed Change Tracking**: Tracks specific field changes (price, availability, etc.)
- **Change Logging**: Stores all changes with timestamps and detailed information

### Logging and Alerts
- **Console Logging**: Real-time output to console
- **File Logging**: Detailed logs saved to `logs/scheduler.log`
- **Change Alerts**: Dedicated change alerts in `logs/change_alerts.log`
- **Error Handling**: Comprehensive error logging and alerting

### Reports
- **Daily Reports**: JSON files in `reports/` directory
- **Change Statistics**: Summary of new, removed, and updated books
- **Price Change Tracking**: Detailed price change analysis

## Monitoring

- **Logs**: Check `logs/` directory for detailed logs
  - `crawler.log`: Crawler activity logs
  - `scheduler.log`: Scheduler and job logs
  - `change_alerts.log`: Change detection alerts
- **Reports**: Check `reports/` directory for daily change reports
- **MongoDB**: Use Mongo Express at http://localhost:8081
- **Metrics**: Crawl sessions and change logs stored in MongoDB

## Troubleshooting

### Common Issues

1. **MongoDB Connection Failed**
   - Ensure Docker containers are running: `docker-compose ps`
   - Check MongoDB logs: `docker-compose logs mongodb`

2. **Crawler Fails to Start**
   - Verify environment variables in `.env`
   - Check network connectivity to target website

3. **High Memory Usage**
   - Reduce `MAX_CONCURRENT_REQUESTS`
   - Disable `STORE_RAW_HTML` if not needed

## License

This project is licensed under the MIT License.
