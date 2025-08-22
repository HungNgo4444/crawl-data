"""Configuration settings"""

import os
from typing import List
from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    """Application settings"""
    
    # API Settings
    app_name: str = Field("Newspaper4k Content Extractor", description="Application name")
    app_version: str = Field("1.0.0", description="Application version")
    host: str = Field("0.0.0.0", description="Host address")
    port: int = Field(8000, description="Port number")
    debug: bool = Field(False, description="Debug mode")
    
    # Database Settings
    database_url: str = Field(
        "postgresql://crawler_user:crawler123@localhost:5432/crawler_db",
        description="Database connection URL"
    )
    
    # Extraction Settings
    default_max_articles: int = Field(50, description="Default maximum articles per domain")
    min_content_length: int = Field(100, description="Minimum content length")
    quality_threshold: float = Field(0.5, description="Quality threshold")
    request_timeout: int = Field(30, description="HTTP request timeout in seconds")
    request_delay: float = Field(1.0, description="Delay between requests in seconds")
    max_retries: int = Field(3, description="Maximum retry attempts")
    
    # Vietnamese Processing
    vietnamese_stopwords_enabled: bool = Field(True, description="Enable Vietnamese stopwords filtering")
    text_cleaning_enabled: bool = Field(True, description="Enable text cleaning")
    
    # User Agent
    user_agent: str = Field(
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        description="User agent for HTTP requests"
    )
    
    # Logging
    log_level: str = Field("INFO", description="Logging level")
    log_format: str = Field(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log format"
    )
    
    # Supported Vietnamese domains
    vietnamese_domains: List[str] = Field(
        default_factory=lambda: [
            "vnexpress.net", "dantri.com.vn", "tuoitre.vn", "thanhnien.vn", 
            "24h.com.vn", "vietnamnet.vn", "kenh14.vn", "zing.vn", "tienphong.vn",
            "laodong.vn", "nguoiduatin.vn", "baomoi.com", "cafef.vn", "doisongphapluat.vn"
        ],
        description="List of supported Vietnamese domains"
    )
    
    class Config:
        env_prefix = "NEWS_EXTRACTOR_"
        case_sensitive = False
        env_file = ".env"


# Global settings instance
_settings = None


def get_settings() -> Settings:
    """Get application settings instance"""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
