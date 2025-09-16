// MongoDB initialization script
db = db.getSiblingDB('book_scraper');

// Create collections with proper indexes
db.createCollection('books');
db.createCollection('crawl_sessions');
db.createCollection('change_logs');

// Create indexes for efficient querying
db.books.createIndex({ "url": 1 }, { unique: true });
db.books.createIndex({ "upc": 1 }, { unique: true });
db.books.createIndex({ "category": 1 });
db.books.createIndex({ "price_including_tax": 1 });
db.books.createIndex({ "price_excluding_tax": 1 });
db.books.createIndex({ "tax_amount": 1 });
db.books.createIndex({ "rating": 1 });
db.books.createIndex({ "availability": 1 });
db.books.createIndex({ "availability_count": 1 });
db.books.createIndex({ "crawl_timestamp": 1 });
db.books.createIndex({ "name": "text", "description": "text" });

// Create indexes for crawl sessions
db.crawl_sessions.createIndex({ "session_id": 1 }, { unique: true });
db.crawl_sessions.createIndex({ "status": 1 });
db.crawl_sessions.createIndex({ "started_at": 1 });

// Create indexes for change logs
db.change_logs.createIndex({ "book_id": 1 });
db.change_logs.createIndex({ "change_type": 1 });
db.change_logs.createIndex({ "timestamp": 1 });

print('Database initialized successfully');
