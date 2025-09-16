from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # MongoDB settings
    mongodb_uri: str = "mongodb://admin:password@localhost:27017/book_scraper?authSource=admin"
    mongodb_database: str = "book_scraper"
    
    # Crawler settings
    base_url: str = "https://books.toscrape.com"
    max_concurrent_requests: int = 10
    request_timeout: int = 30
    retry_attempts: int = 3
    retry_delay: float = 1.0
    rate_limit_delay: float = 0.1  # Delay between requests in seconds
    
    # Storage settings
    store_raw_html: bool = True
    
    # Logging settings
    log_level: str = "INFO"
    
    # API settings
    api_key: str = "default-api-key"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Global settings instance
settings = Settings()
