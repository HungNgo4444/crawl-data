import os
from typing import Optional, List, Dict, Any
from pydantic import Field
from pydantic_settings import BaseSettings
from enum import Enum


class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class CrawlMode(str, Enum):
    DEVELOPMENT = "development"
    PRODUCTION = "production"
    TESTING = "testing"


class Settings(BaseSettings):
    """Application settings"""
    
    # Application settings
    app_name: str = "Crawl4AI Domain Monitor"
    app_version: str = "1.0.0"
    debug: bool = Field(default=False, env="DEBUG")
    mode: CrawlMode = Field(default=CrawlMode.PRODUCTION, env="CRAWL_MODE")
    
    # API settings
    api_host: str = Field(default="0.0.0.0", env="API_HOST")
    api_port: int = Field(default=8002, env="API_PORT")
    api_workers: int = Field(default=1, env="API_WORKERS")
    
    # Database settings
    db_host: str = Field(default="postgres", env="POSTGRES_HOST")
    db_port: int = Field(default=5432, env="POSTGRES_PORT")
    db_name: str = Field(default="crawler_db", env="POSTGRES_DB")
    db_user: str = Field(default="crawler_user", env="POSTGRES_USER")
    db_password: str = Field(default="crawler123", env="POSTGRES_PASSWORD")
    
    # Newspaper4k integration settings
    newspaper4k_base_url: str = Field(default="http://localhost:8001", env="NEWSPAPER4K_BASE_URL")
    newspaper4k_timeout: int = Field(default=30, env="NEWSPAPER4K_TIMEOUT")
    newspaper4k_max_retries: int = Field(default=3, env="NEWSPAPER4K_MAX_RETRIES")
    newspaper4k_retry_delay: float = Field(default=2.0, env="NEWSPAPER4K_RETRY_DELAY")
    
    # Crawl4AI settings
    crawl4ai_browser_type: str = Field(default="chromium", env="CRAWL4AI_BROWSER_TYPE")
    crawl4ai_headless: bool = Field(default=True, env="CRAWL4AI_HEADLESS")
    crawl4ai_stealth_mode: bool = Field(default=True, env="CRAWL4AI_STEALTH_MODE")
    crawl4ai_requests_per_minute: int = Field(default=30, env="CRAWL4AI_RATE_LIMIT")
    crawl4ai_burst_limit: int = Field(default=5, env="CRAWL4AI_BURST_LIMIT")
    crawl4ai_timeout: int = Field(default=30000, env="CRAWL4AI_TIMEOUT")
    
    # Queue management settings
    queue_max_size: int = Field(default=10000, env="QUEUE_MAX_SIZE")
    queue_batch_size: int = Field(default=10, env="QUEUE_BATCH_SIZE")
    queue_max_concurrent: int = Field(default=3, env="QUEUE_MAX_CONCURRENT")
    queue_cleanup_days: int = Field(default=7, env="QUEUE_CLEANUP_DAYS")
    
    # URL deduplication settings
    dedup_ttl_days: int = Field(default=30, env="DEDUP_TTL_DAYS")
    dedup_hash_algorithm: str = Field(default="sha256", env="DEDUP_HASH_ALGORITHM")
    dedup_cleanup_interval_hours: int = Field(default=24, env="DEDUP_CLEANUP_INTERVAL")
    
    # Monitoring settings
    monitoring_interval_seconds: int = Field(default=300, env="MONITORING_INTERVAL")
    monitoring_max_domains_concurrent: int = Field(default=3, env="MONITORING_MAX_CONCURRENT")
    monitoring_health_check_interval: int = Field(default=60, env="HEALTH_CHECK_INTERVAL")
    
    # Logging settings
    log_level: LogLevel = Field(default=LogLevel.INFO, env="LOG_LEVEL")
    log_file: Optional[str] = Field(default=None, env="LOG_FILE")
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        env="LOG_FORMAT"
    )
    
    # Security settings
    api_key: Optional[str] = Field(default=None, env="API_KEY")
    allowed_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8080"],
        env="ALLOWED_ORIGINS"
    )
    
    # Performance settings
    max_memory_usage_mb: int = Field(default=2048, env="MAX_MEMORY_USAGE_MB")
    memory_check_interval: int = Field(default=300, env="MEMORY_CHECK_INTERVAL")
    
    # Vietnamese news site specific settings
    vietnamese_domains_priority: bool = Field(default=True, env="VN_DOMAINS_PRIORITY")
    vietnamese_encoding: str = Field(default="utf-8", env="VN_ENCODING")
    vietnamese_user_agent: str = Field(
        default="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        env="VN_USER_AGENT"
    )
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
    
    def get_database_config(self) -> Dict[str, Any]:
        """Get database configuration"""
        return {
            'host': self.db_host,
            'port': self.db_port,
            'database': self.db_name,
            'user': self.db_user,
            'password': self.db_password
        }
    
    def get_crawl4ai_config(self) -> Dict[str, Any]:
        """Get crawl4ai configuration"""
        return {
            'browser_type': self.crawl4ai_browser_type,
            'headless': self.crawl4ai_headless,
            'stealth_mode': self.crawl4ai_stealth_mode,
            'requests_per_minute': self.crawl4ai_requests_per_minute,
            'burst_limit': self.crawl4ai_burst_limit,
            'timeout': self.crawl4ai_timeout,
            'user_agent': self.vietnamese_user_agent
        }
    
    def get_newspaper4k_config(self) -> Dict[str, Any]:
        """Get newspaper4k client configuration"""
        return {
            'base_url': self.newspaper4k_base_url,
            'timeout': self.newspaper4k_timeout,
            'max_retries': self.newspaper4k_max_retries,
            'retry_delay': self.newspaper4k_retry_delay
        }
    
    def get_queue_config(self) -> Dict[str, Any]:
        """Get queue management configuration"""
        return {
            'max_size': self.queue_max_size,
            'batch_size': self.queue_batch_size,
            'max_concurrent': self.queue_max_concurrent,
            'cleanup_days': self.queue_cleanup_days
        }
    
    def get_deduplication_config(self) -> Dict[str, Any]:
        """Get URL deduplication configuration"""
        return {
            'ttl_days': self.dedup_ttl_days,
            'hash_algorithm': self.dedup_hash_algorithm,
            'cleanup_interval_hours': self.dedup_cleanup_interval_hours
        }
    
    def get_monitoring_config(self) -> Dict[str, Any]:
        """Get monitoring configuration"""
        return {
            'interval_seconds': self.monitoring_interval_seconds,
            'max_concurrent': self.monitoring_max_domains_concurrent,
            'health_check_interval': self.monitoring_health_check_interval
        }
    
    def is_development(self) -> bool:
        """Check if running in development mode"""
        return self.mode == CrawlMode.DEVELOPMENT
    
    def is_production(self) -> bool:
        """Check if running in production mode"""
        return self.mode == CrawlMode.PRODUCTION
    
    def is_testing(self) -> bool:
        """Check if running in testing mode"""
        return self.mode == CrawlMode.TESTING


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings"""
    return settings


def update_settings(**kwargs) -> Settings:
    """Update settings with new values"""
    global settings
    for key, value in kwargs.items():
        if hasattr(settings, key):
            setattr(settings, key, value)
    return settings