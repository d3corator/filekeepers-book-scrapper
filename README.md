# Book Scraper

A scalable and fault-tolerant web crawling solution with automated change detection and scheduling for https://books.toscrape.com.

## Features

- **Async Web Crawling**: High-performance async crawling using httpx
- **MongoDB Storage**: NoSQL database with proper indexing and schema
- **RESTful API**: FastAPI-based API with authentication and filtering
- **Retry Logic**: Robust error handling with configurable retry attempts
- **Resume Functionality**: Resume from last successful crawl in case of failure
- **Change Detection**: Automated detection of new, updated, and removed books
- **Scheduled Monitoring**: Daily change detection and weekly full crawls
- **Comprehensive Logging**: Detailed logging with change alerts and reports
- **Daily Reports**: JSON reports of daily changes and statistics

## Requirements

- **Python**: 3.11 or higher
- **Docker**: For MongoDB database
- **PDM**: Python Dependency Manager

## Dependencies

### Core Dependencies
- **httpx** >= 0.27.0 - Async HTTP client
- **pydantic** >= 2.7.0 - Data validation and settings
- **pydantic-settings** >= 2.3.0 - Settings management
- **pymongo** >= 4.6.0 - MongoDB driver
- **beautifulsoup4** >= 4.12.0 - HTML parsing
- **apscheduler** >= 3.10.4 - Job scheduling
- **fastapi** >= 0.115.0 - Web API framework
- **uvicorn[standard]** >= 0.30.0 - ASGI server
- **python-multipart** >= 0.0.6 - Form data handling
- **python-jose[cryptography]** >= 3.3.0 - JWT handling
- **passlib[bcrypt]** >= 1.7.4 - Password hashing
- **slowapi** >= 0.1.9 - Rate limiting

### Development Dependencies
- **pytest** >= 8.2.0 - Testing framework
- **pytest-asyncio** >= 0.23.7 - Async testing support
- **coverage** >= 7.6.0 - Code coverage
- **respx** >= 0.21.1 - HTTP mocking
- **ruff** >= 0.6.0 - Linting
- **black** >= 24.8.0 - Code formatting
- **mypy** >= 1.10.0 - Type checking

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
├── api/             # RESTful API
│   ├── app.py       # FastAPI application
│   ├── auth.py      # Authentication and authorization
│   ├── schemas.py   # API request/response schemas
│   └── routers/     # API route handlers
│       ├── books.py # Book-related endpoints
│       ├── changes.py # Change log endpoints
│       └── health.py # Health check endpoint
└── utils/           # Configuration and utilities
```

## Quick Start

### 1. Prerequisites

Ensure you have the following installed:
- **Python 3.11+** - [Download from python.org](https://www.python.org/downloads/)
- **Docker & Docker Compose** - [Download from docker.com](https://www.docker.com/get-started)
- **PDM** - Python Dependency Manager

### 2. Install PDM

```bash
# Recommended: Install via pipx
pipx install pdm

# Alternative: Install via pip
pip install --user pdm
```

### 3. Clone and Setup Project

```bash
# Clone the repository
git clone <repository-url>
cd book-scraper

# Create virtual environment with Python 3.11
pdm venv create -f 3.11

# Activate the virtual environment
pdm use -f $(pdm venv list --path | tail -1)

# Install all dependencies (production + development)
pdm install -G :all
```

### 4. Start MongoDB Database

```bash
# Start MongoDB and Mongo Express using Docker Compose
docker-compose up -d

# Verify services are running
docker-compose ps
```

**Database Access:**
- **MongoDB**: `localhost:27017`
- **Mongo Express** (Web UI): http://localhost:8081
  - Username: `admin`
  - Password: `admin`

### 5. Configure Environment

```bash
# Copy the example environment file
cp env.example .env

# Edit the .env file with your preferred settings
nano .env  # or use your preferred editor
```

**Important**: Update the `API_KEY` in your `.env` file for production use!

## Environment Configuration

The application uses environment variables for configuration. Copy `env.example` to `.env` and customize as needed:

```bash
# MongoDB Configuration
MONGODB_URI=mongodb://admin:password@localhost:27017/book_scraper?authSource=admin
MONGODB_DATABASE=book_scraper

# Crawler Configuration
BASE_URL=https://books.toscrape.com
MAX_CONCURRENT_REQUESTS=10
REQUEST_TIMEOUT=30
RETRY_ATTEMPTS=3
RETRY_DELAY=1.0
RATE_LIMIT_DELAY=0.1

# Storage Configuration
STORE_RAW_HTML=true

# Logging Configuration
LOG_LEVEL=INFO

# API Configuration
API_KEY=default-api-key
```

### Configuration Options

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
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `API_KEY` | `default-api-key` | API key for authentication |

## Verify Installation

After completing the setup, verify everything is working:

```bash
# 1. Check if dependencies are installed correctly
pdm run python -c "import httpx, pymongo, fastapi; print('✅ Dependencies installed successfully')"

# 2. Test database connection
pdm run python -c "
import asyncio
from src.crawler.storage import MongoDBStorage
async def test_db():
    storage = MongoDBStorage()
    await storage.connect()
    print('✅ Database connection successful')
    await storage.disconnect()
asyncio.run(test_db())
"

# 3. Run tests to verify everything works
pdm run test

# 4. Start the API server (optional)
pdm run api
# Then visit http://localhost:8000/docs to see the API documentation
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

### Run API Server

```bash
# Start the FastAPI server
pdm run api

# The API will be available at http://localhost:8000
# API documentation at http://localhost:8000/docs
```

## API Endpoints

The RESTful API provides access to crawled book data and change logs with authentication and filtering capabilities.

### Authentication

All API endpoints require authentication using an API key:

```bash
# Include API key in request headers
curl -H "Authorization: Bearer your-api-key" http://localhost:8000/api/v1/books
```

**Default API Key**: `default-api-key` (change in production!)

### Base URL

All API endpoints are prefixed with `/api/v1/`

### Books Endpoints

#### Get All Books

```http
GET /api/v1/books
```

**Query Parameters:**
- `page` (int, default: 1): Page number
- `per_page` (int, default: 20, max: 100): Items per page
- `category` (string, optional): Filter by book category
- `min_price` (float, optional): Minimum price filter
- `max_price` (float, optional): Maximum price filter
- `availability` (string, optional): Filter by availability status
- `sort_by` (string, default: "name"): Sort field (name, price_including_tax, rating, crawl_timestamp)
- `sort_order` (string, default: "asc"): Sort order (asc, desc)

**Example:**
```bash
curl -H "Authorization: Bearer default-api-key" \
  "http://localhost:8000/api/v1/books?page=1&per_page=10&category=Fiction&sort_by=price_including_tax&sort_order=desc"
```

**Response:**
```json
{
  "books": [
    {
      "name": "Book Title",
      "description": "Book description...",
      "category": "Fiction",
      "upc": "123456789",
      "price_including_tax": 19.99,
      "price_excluding_tax": 16.66,
      "tax_amount": 3.33,
      "availability": "In stock (22 available)",
      "availability_count": 22,
      "number_of_reviews": 5,
      "rating": 3,
      "image_url": "https://books.toscrape.com/media/...",
      "url": "https://books.toscrape.com/catalogue/...",
      "crawl_timestamp": "2024-01-01T12:00:00Z"
    }
  ],
  "total": 1000,
  "page": 1,
  "per_page": 10,
  "total_pages": 100,
  "has_next": true,
  "has_prev": false
}
```

#### Get Book by ID

```http
GET /api/v1/books/{book_id}
```

**Parameters:**
- `book_id` (string): Book UPC (Universal Product Code)

**Example:**
```bash
curl -H "Authorization: Bearer default-api-key" \
  "http://localhost:8000/api/v1/books/123456789"
```

**Response:**
```json
{
  "name": "Book Title",
  "description": "Book description...",
  "category": "Fiction",
  "upc": "123456789",
  "price_including_tax": 19.99,
  "price_excluding_tax": 16.66,
  "tax_amount": 3.33,
  "availability": "In stock (22 available)",
  "availability_count": 22,
  "number_of_reviews": 5,
  "rating": 3,
  "image_url": "https://books.toscrape.com/media/...",
  "url": "https://books.toscrape.com/catalogue/...",
  "crawl_timestamp": "2024-01-01T12:00:00Z"
}
```

### Changes Endpoints

#### Get Change Logs

```http
GET /api/v1/changes
```

**Query Parameters:**
- `page` (int, default: 1): Page number
- `per_page` (int, default: 20, max: 100): Items per page
- `change_type` (string, optional): Filter by change type (new, updated, removed)
- `book_id` (string, optional): Filter by book UPC

**Example:**
```bash
curl -H "Authorization: Bearer default-api-key" \
  "http://localhost:8000/api/v1/changes?change_type=updated&page=1&per_page=10"
```

**Response:**
```json
{
  "changes": [
    {
      "book_id": "123456789",
      "change_type": "updated",
      "field_changes": {
        "price_including_tax": {
          "old": "19.99",
          "new": "24.99"
        }
      },
      "timestamp": "2024-01-01T12:00:00Z",
      "session_id": "session-uuid"
    }
  ],
  "total": 50,
  "page": 1,
  "per_page": 10,
  "total_pages": 5,
  "has_next": true,
  "has_prev": false
}
```

### Health Check

```http
GET /api/v1/health
```

**Example:**
```bash
curl "http://localhost:8000/api/v1/health"
```

**Response:**
```json
{
  "status": "ok",
  "version": "0.1.0"
}
```

### Error Responses

All endpoints return consistent error responses:

```json
{
  "error": "Error message",
  "detail": "Detailed error description"
}
```

**Common HTTP Status Codes:**
- `200`: Success
- `400`: Bad Request (invalid parameters)
- `401`: Unauthorized (missing API key)
- `403`: Forbidden (invalid API key)
- `404`: Not Found (resource not found)
- `500`: Internal Server Error

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

### Getting Help

- **Check logs**: Review files in `logs/` directory
- **Console output**: Look for detailed error messages
- **Database**: Use Mongo Express at http://localhost:8081 to inspect data
- **API docs**: Visit http://localhost:8000/docs when API is running
- **Dependencies**: Ensure all prerequisites are installed correctly
