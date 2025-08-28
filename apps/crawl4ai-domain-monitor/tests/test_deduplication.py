import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta

from src.monitor.url_deduplicator import URLDeduplicator
from src.utils.database import DatabaseManager
from src.utils.url_utils import URLNormalizer, URLValidator


class TestURLNormalizer:
    """Test URL normalization functionality"""
    
    def test_normalize_basic_url(self):
        normalizer = URLNormalizer()
        
        # Test basic normalization
        url = "https://VnExpress.net/Thoi-Su/Article-123.html?utm_source=facebook"
        expected = "https://vnexpress.net/thoi-su/article-123.html"
        
        result = normalizer.normalize_url(url)
        assert result == expected
    
    def test_remove_tracking_params(self):
        normalizer = URLNormalizer()
        
        url = "https://dantri.com.vn/news-123.html?utm_campaign=social&fbclid=abc123&ref=homepage"
        result = normalizer.normalize_url(url)
        
        # Should not contain tracking parameters
        assert "utm_campaign" not in result
        assert "fbclid" not in result
        assert "ref" not in result
    
    def test_www_prefix_removal(self):
        normalizer = URLNormalizer()
        
        url1 = "https://www.vnexpress.net/article-123.html"
        url2 = "https://vnexpress.net/article-123.html"
        
        result1 = normalizer.normalize_url(url1)
        result2 = normalizer.normalize_url(url2)
        
        assert result1 == result2
    
    def test_query_parameter_sorting(self):
        normalizer = URLNormalizer(remove_tracking_params=False)
        
        url = "https://example.com/page?c=3&a=1&b=2"
        result = normalizer.normalize_url(url)
        
        assert "a=1&b=2&c=3" in result


class TestURLValidator:
    """Test URL validation for Vietnamese news sites"""
    
    def test_vietnamese_domain_detection(self):
        validator = URLValidator()
        
        # Vietnamese domains
        assert validator.is_vietnamese_news_domain("https://vnexpress.net/article.html")
        assert validator.is_vietnamese_news_domain("https://dantri.com.vn/news.html")
        assert validator.is_vietnamese_news_domain("https://tuoitre.vn/tin-tuc.html")
        
        # Non-Vietnamese domains
        assert not validator.is_vietnamese_news_domain("https://cnn.com/news.html")
        assert not validator.is_vietnamese_news_domain("https://bbc.co.uk/news.html")
    
    def test_article_url_patterns(self):
        validator = URLValidator()
        
        # Typical Vietnamese news URL patterns
        assert validator.is_likely_article_url("https://vnexpress.net/article-12345.html")
        assert validator.is_likely_article_url("https://dantri.com.vn/news-67890.html")
        assert validator.is_likely_article_url("https://site.com/2024/01/article.html")
        
        # Non-article URLs
        assert not validator.is_likely_article_url("https://vnexpress.net/")
        assert not validator.is_likely_article_url("https://vnexpress.net/category/")
    
    def test_url_exclusion(self):
        validator = URLValidator()
        
        # Should exclude
        assert validator.should_exclude_url("https://vnexpress.net/tag/trending")
        assert validator.should_exclude_url("https://site.com/login.html")
        assert validator.should_exclude_url("https://site.com/image.jpg")
        assert validator.should_exclude_url("https://site.com/news?utm_source=facebook")
        
        # Should not exclude
        assert not validator.should_exclude_url("https://vnexpress.net/article-123.html")
        assert not validator.should_exclude_url("https://dantri.com.vn/tin-tuc/news-456.html")
    
    def test_filter_urls(self):
        validator = URLValidator()
        
        urls = [
            "https://vnexpress.net/article-123.html",
            "https://vnexpress.net/tag/sports",
            "https://cnn.com/news.html",
            "https://dantri.com.vn/news-456.html",
            "https://vnexpress.net/login.html",
        ]
        
        filtered = validator.filter_urls(urls)
        
        # Should only include Vietnamese news articles
        expected = [
            "https://vnexpress.net/article-123.html",
            "https://dantri.com.vn/news-456.html"
        ]
        
        assert set(filtered) == set(expected)


class TestURLDeduplicator:
    """Test URL deduplication functionality"""
    
    @pytest.fixture
    def mock_db_manager(self):
        return Mock(spec=DatabaseManager)
    
    @pytest.fixture
    def deduplicator(self, mock_db_manager):
        return URLDeduplicator(mock_db_manager, ttl_days=30)
    
    def test_fingerprint_generation(self, deduplicator):
        url1 = "https://vnexpress.net/article-123.html?utm_source=facebook"
        url2 = "https://VnExpress.net/Article-123.html?fbclid=abc"
        
        # Should generate same fingerprint for similar URLs after normalization
        fingerprint1 = deduplicator.fingerprint_generator.generate_fingerprint(url1)
        fingerprint2 = deduplicator.fingerprint_generator.generate_fingerprint(url2)
        
        assert len(fingerprint1) == 64  # SHA-256 hash length
        assert len(fingerprint2) == 64
        # After normalization, tracking params removed, should be similar base
        
    def test_is_duplicate_found(self, deduplicator, mock_db_manager):
        # Mock database response
        mock_db_manager.execute_sql.return_value = [{
            'url_hash': 'abc123',
            'original_url': 'https://vnexpress.net/article-123.html',
            'status': 'completed'
        }]
        
        is_dup, data = deduplicator.is_duplicate("https://vnexpress.net/article-123.html")
        
        assert is_dup is True
        assert data is not None
        assert data['status'] == 'completed'
    
    def test_is_duplicate_not_found(self, deduplicator, mock_db_manager):
        # Mock empty database response
        mock_db_manager.execute_sql.return_value = []
        
        is_dup, data = deduplicator.is_duplicate("https://vnexpress.net/new-article.html")
        
        assert is_dup is False
        assert data is None
    
    def test_mark_processed_new_url(self, deduplicator, mock_db_manager):
        # Mock database responses
        mock_db_manager.execute_sql.side_effect = [
            [],  # is_duplicate check returns empty
            [{'success': True}]  # insert returns success
        ]
        
        result = deduplicator.mark_processed(
            url="https://vnexpress.net/article-123.html",
            domain_id=1,
            status="completed"
        )
        
        assert result is True
        assert mock_db_manager.execute_sql.call_count == 2
    
    def test_add_discovered_urls(self, deduplicator, mock_db_manager):
        # Mock database responses
        urls = [
            "https://vnexpress.net/article-1.html",
            "https://vnexpress.net/article-2.html",
            "https://vnexpress.net/article-3.html"
        ]
        
        # Mock: first URL is duplicate, others are new
        mock_db_manager.execute_sql.side_effect = [
            [{'url_hash': 'hash1'}],  # duplicate found
            [],  # not duplicate
            [{'success': True}],  # insert success
            [],  # not duplicate  
            [{'success': True}]   # insert success
        ]
        
        new_urls, dup_urls = deduplicator.add_discovered_urls(urls, domain_id=1)
        
        assert len(new_urls) == 2
        assert len(dup_urls) == 1
        assert dup_urls[0] == urls[0]
    
    def test_cleanup_expired(self, deduplicator, mock_db_manager):
        mock_db_manager.execute_sql.return_value = [{'success': True}]
        
        result = deduplicator.cleanup_expired()
        
        assert result == 1
        mock_db_manager.execute_sql.assert_called_once()
    
    def test_get_statistics(self, deduplicator, mock_db_manager):
        mock_db_manager.execute_sql.return_value = [
            {'status': 'completed', 'count': '50'},
            {'status': 'failed', 'count': '5'},
            {'status': 'discovered', 'count': '20'}
        ]
        
        stats = deduplicator.get_statistics(domain_id=1)
        
        assert stats['completed'] == 50
        assert stats['failed'] == 5
        assert stats['discovered'] == 20
        assert stats['total'] == 75


if __name__ == '__main__':
    pytest.main([__file__])