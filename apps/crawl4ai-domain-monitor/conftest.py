"""
PyTest configuration for crawl4ai-domain-monitor
"""
import os
import sys
from pathlib import Path

# Add the project root directory to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Add the src directory to Python path
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

# Set test environment variables
os.environ["CRAWL_MODE"] = "testing"
os.environ["DEBUG"] = "true"
os.environ["LOG_LEVEL"] = "DEBUG"

# Mock external dependencies that might not be available during testing
import pytest
from unittest.mock import Mock

# Mock crawl4ai if not available
try:
    import crawl4ai
except ImportError:
    sys.modules['crawl4ai'] = Mock()
    sys.modules['crawl4ai.AsyncWebCrawler'] = Mock()
    sys.modules['crawl4ai.BrowserConfig'] = Mock()
    sys.modules['crawl4ai.CrawlerRunConfig'] = Mock()
    sys.modules['crawl4ai.CacheMode'] = Mock()
    sys.modules['crawl4ai.extraction_strategy'] = Mock()
    sys.modules['crawl4ai.extraction_strategy.JsonCssExtractionStrategy'] = Mock()

# Mock other optional dependencies
try:
    import psutil
except ImportError:
    sys.modules['psutil'] = Mock()

try:
    import feedparser
except ImportError:
    sys.modules['feedparser'] = Mock()


@pytest.fixture
def mock_docker_env():
    """Mock Docker environment for testing"""
    with pytest.MonkeyPatch.context() as m:
        m.setenv("DB_CONTAINER_NAME", "test_postgres")
        m.setenv("DB_NAME", "test_db")
        m.setenv("DB_USER", "test_user")
        m.setenv("DB_PASSWORD", "test123")
        yield


@pytest.fixture
def test_database_config():
    """Test database configuration"""
    return {
        'container_name': 'test_postgres',
        'database': 'test_db',
        'user': 'test_user',
        'password': 'test123'
    }


@pytest.fixture
def test_domain_config():
    """Test domain configuration"""
    from src.models.domain_config import DomainConfig
    
    return DomainConfig(
        id=1,
        name="test.vn",
        display_name="Test Domain",
        base_url="https://test.vn",
        monitoring_pages=["https://test.vn", "https://test.vn/news"],
        rss_feeds=["https://test.vn/rss.xml"],
        url_patterns=[r"https://test\.vn/.*-\d+\.html$"],
        exclude_patterns=["/tag/", "/video/", "?utm_"]
    )


@pytest.fixture
def sample_vietnamese_urls():
    """Sample Vietnamese news URLs for testing"""
    return [
        "https://vnexpress.net/article-123456.html",
        "https://dantri.com.vn/news-789012.html",
        "https://tuoitre.vn/tin-tuc-345678.html",
        "https://thanhnien.vn/bai-viet-901234.html",
        "https://24h.com.vn/tin-nong-567890.html"
    ]


@pytest.fixture
def malicious_sql_inputs():
    """Sample SQL injection attempts for security testing"""
    return [
        "'; DROP TABLE url_tracking; --",
        "' OR '1'='1",
        "' UNION SELECT * FROM users --",
        "'; DELETE FROM domains; --",
        "Robert'; DROP TABLE students; --"
    ]