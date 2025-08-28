import pytest
from unittest.mock import Mock, AsyncMock, patch
import asyncio

from src.monitor.crawl4ai_wrapper import Crawl4aiWrapper
from src.models.domain_config import DomainConfig
from src.utils.crawl4ai_utils import Crawl4AIConfig


@pytest.fixture
def domain_config():
    return DomainConfig(
        id=1,
        name="vnexpress.net",
        display_name="VnExpress",
        base_url="https://vnexpress.net",
        monitoring_pages=["https://vnexpress.net", "https://vnexpress.net/thoi-su"],
        rss_feeds=["https://vnexpress.net/rss/tin-moi-nhat.rss"],
        url_patterns=[r"https://vnexpress\.net/.*-\d+\.html$"],
        exclude_patterns=["/tag/", "/video/", "?utm_"]
    )


@pytest.fixture
def crawl4ai_wrapper():
    return Crawl4aiWrapper(max_retries=1, retry_delay=0.1)


class TestCrawl4AIConfig:
    """Test crawl4ai configuration utilities"""
    
    def test_create_browser_config(self):
        config = Crawl4AIConfig.create_browser_config(
            headless=True,
            browser_type="chromium",
            stealth_mode=True
        )
        
        assert config.headless is True
        assert config.browser_type == "chromium"
        assert config.viewport_width == 1920
        assert config.viewport_height == 1080
        assert len(config.extra_args) > 0
        assert '--lang=vi-VN' in config.extra_args
    
    def test_create_crawler_config(self):
        from crawl4ai import CacheMode
        
        config = Crawl4AIConfig.create_crawler_config(
            cache_mode=CacheMode.BYPASS,
            word_count_threshold=10,
            css_selector='a[href]'
        )
        
        assert config.cache_mode == CacheMode.BYPASS
        assert config.word_count_threshold == 10
        assert config.css_selector == 'a[href]'
        assert config.remove_overlay_elements is True
    
    def test_get_vietnamese_news_selectors(self):
        selectors = Crawl4AIConfig.get_vietnamese_news_selectors()
        
        assert 'article_links' in selectors
        assert 'navigation_links' in selectors
        assert 'category_links' in selectors
        assert 'exclude_links' in selectors
        
        # Check Vietnamese-specific patterns
        assert '/tin-tuc/' in selectors['article_links']
        assert '/chuyen-muc/' in selectors['category_links']
    
    def test_create_link_extraction_strategy(self):
        strategy = Crawl4AIConfig.create_link_extraction_strategy()
        
        assert strategy['name'] == 'vietnamese_news_links'
        assert 'schema' in strategy
        assert 'extraction_map' in strategy
        assert 'article_links' in strategy['extraction_map']
        assert 'category_links' in strategy['extraction_map']


class TestCrawl4aiWrapper:
    """Test Crawl4aiWrapper functionality"""
    
    @pytest.mark.asyncio
    async def test_discover_urls_from_page_success(self, crawl4ai_wrapper, domain_config):
        # Mock crawl4ai response
        mock_result = Mock()
        mock_result.success = True
        mock_result.extracted_content = {
            'article_links': [
                {'url': 'https://vnexpress.net/article-123.html', 'title': 'Test Article'},
                {'url': 'https://vnexpress.net/news-456.html', 'title': 'Test News'}
            ],
            'category_links': [
                {'url': 'https://vnexpress.net/thoi-su', 'title': 'Thời sự'}
            ]
        }
        
        # Mock AsyncWebCrawler
        with patch('src.monitor.crawl4ai_wrapper.AsyncWebCrawler') as mock_crawler_class:
            mock_crawler = AsyncMock()
            mock_crawler.arun = AsyncMock(return_value=mock_result)
            mock_crawler_class.return_value.__aenter__ = AsyncMock(return_value=mock_crawler)
            mock_crawler_class.return_value.__aexit__ = AsyncMock(return_value=None)
            
            urls = await crawl4ai_wrapper.discover_urls_from_page(
                "https://vnexpress.net", 
                domain_config
            )
            
            assert len(urls) > 0
            assert all('vnexpress.net' in url for url in urls)
    
    @pytest.mark.asyncio
    async def test_discover_urls_from_page_failure(self, crawl4ai_wrapper, domain_config):
        # Mock failed crawl4ai response
        mock_result = Mock()
        mock_result.success = False
        mock_result.error_message = "Page load timeout"
        mock_result.extracted_content = None
        
        with patch('src.monitor.crawl4ai_wrapper.AsyncWebCrawler') as mock_crawler_class:
            mock_crawler = AsyncMock()
            mock_crawler.arun = AsyncMock(return_value=mock_result)
            mock_crawler_class.return_value.__aenter__ = AsyncMock(return_value=mock_crawler)
            mock_crawler_class.return_value.__aexit__ = AsyncMock(return_value=None)
            
            urls = await crawl4ai_wrapper.discover_urls_from_page(
                "https://vnexpress.net", 
                domain_config
            )
            
            assert urls == []
    
    @pytest.mark.asyncio
    async def test_discover_urls_from_rss_success(self, crawl4ai_wrapper, domain_config):
        # Mock RSS content
        rss_content = """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
            <channel>
                <item>
                    <link>https://vnexpress.net/article-789.html</link>
                    <title>RSS Article 1</title>
                </item>
                <item>
                    <link>https://vnexpress.net/article-101.html</link>
                    <title>RSS Article 2</title>
                </item>
            </channel>
        </rss>"""
        
        # Mock crawl4ai response
        mock_result = Mock()
        mock_result.success = True
        mock_result.html = rss_content
        
        with patch('src.monitor.crawl4ai_wrapper.AsyncWebCrawler') as mock_crawler_class:
            mock_crawler = AsyncMock()
            mock_crawler.arun = AsyncMock(return_value=mock_result)
            mock_crawler_class.return_value.__aenter__ = AsyncMock(return_value=mock_crawler)
            mock_crawler_class.return_value.__aexit__ = AsyncMock(return_value=None)
            
            urls = await crawl4ai_wrapper.discover_urls_from_rss(
                "https://vnexpress.net/rss.xml",
                domain_config
            )
            
            assert len(urls) > 0
            assert all('vnexpress.net' in url for url in urls)
            assert all('.html' in url for url in urls)
    
    def test_filter_urls_by_config(self, crawl4ai_wrapper, domain_config):
        test_urls = [
            "https://vnexpress.net/article-123.html",  # Should pass
            "https://vnexpress.net/news-456.html",     # Should pass
            "https://vnexpress.net/tag/trending",      # Should be excluded
            "https://other-site.com/article.html",    # Wrong domain
            "https://vnexpress.net/video/clip.html",  # Should be excluded
            "https://vnexpress.net/article-789.html?utm_source=fb"  # Should be excluded
        ]
        
        filtered = crawl4ai_wrapper._filter_urls_by_config(test_urls, domain_config)
        
        # Should only include valid article URLs from vnexpress.net
        assert len(filtered) == 2
        assert "https://vnexpress.net/article-123.html" in filtered
        assert "https://vnexpress.net/news-456.html" in filtered
        assert all('vnexpress.net' in url for url in filtered)
    
    @pytest.mark.asyncio
    async def test_discover_urls_batch(self, crawl4ai_wrapper, domain_config):
        urls = [
            "https://vnexpress.net",
            "https://vnexpress.net/rss.xml"
        ]
        
        # Mock different responses for different URLs
        def mock_arun_side_effect(*args, **kwargs):
            url = args[0] if args else kwargs.get('url', '')
            
            if 'rss.xml' in url:
                # RSS response
                mock_result = Mock()
                mock_result.success = True
                mock_result.html = '<?xml version="1.0"?><rss><channel><item><link>https://vnexpress.net/rss-article.html</link></item></channel></rss>'
                return mock_result
            else:
                # Page response
                mock_result = Mock()
                mock_result.success = True
                mock_result.extracted_content = {
                    'article_links': [
                        {'url': 'https://vnexpress.net/page-article.html'}
                    ]
                }
                return mock_result
        
        with patch('src.monitor.crawl4ai_wrapper.AsyncWebCrawler') as mock_crawler_class:
            mock_crawler = AsyncMock()
            mock_crawler.arun = AsyncMock(side_effect=mock_arun_side_effect)
            mock_crawler_class.return_value.__aenter__ = AsyncMock(return_value=mock_crawler)
            mock_crawler_class.return_value.__aexit__ = AsyncMock(return_value=None)
            
            results = await crawl4ai_wrapper.discover_urls_batch(urls, domain_config)
            
            assert len(results) == 2
            assert all(isinstance(result, list) for result in results.values())
    
    @pytest.mark.asyncio
    async def test_test_url_accessibility_success(self, crawl4ai_wrapper):
        mock_result = Mock()
        mock_result.success = True
        
        with patch('src.monitor.crawl4ai_wrapper.AsyncWebCrawler') as mock_crawler_class:
            mock_crawler = AsyncMock()
            mock_crawler.arun = AsyncMock(return_value=mock_result)
            mock_crawler_class.return_value.__aenter__ = AsyncMock(return_value=mock_crawler)
            mock_crawler_class.return_value.__aexit__ = AsyncMock(return_value=None)
            
            is_accessible, error = await crawl4ai_wrapper.test_url_accessibility(
                "https://vnexpress.net"
            )
            
            assert is_accessible is True
            assert error is None
    
    @pytest.mark.asyncio
    async def test_test_url_accessibility_failure(self, crawl4ai_wrapper):
        mock_result = Mock()
        mock_result.success = False
        mock_result.error_message = "Connection timeout"
        
        with patch('src.monitor.crawl4ai_wrapper.AsyncWebCrawler') as mock_crawler_class:
            mock_crawler = AsyncMock()
            mock_crawler.arun = AsyncMock(return_value=mock_result)
            mock_crawler_class.return_value.__aenter__ = AsyncMock(return_value=mock_crawler)
            mock_crawler_class.return_value.__aexit__ = AsyncMock(return_value=None)
            
            is_accessible, error = await crawl4ai_wrapper.test_url_accessibility(
                "https://invalid-site.com"
            )
            
            assert is_accessible is False
            assert "Connection timeout" in error
    
    @pytest.mark.asyncio
    async def test_get_page_metadata(self, crawl4ai_wrapper):
        mock_result = Mock()
        mock_result.success = True
        mock_result.metadata = {
            'title': 'Test Page Title',
            'description': 'Test page description'
        }
        mock_result.status_code = 200
        
        with patch('src.monitor.crawl4ai_wrapper.AsyncWebCrawler') as mock_crawler_class:
            mock_crawler = AsyncMock()
            mock_crawler.arun = AsyncMock(return_value=mock_result)
            mock_crawler_class.return_value.__aenter__ = AsyncMock(return_value=mock_crawler)
            mock_crawler_class.return_value.__aexit__ = AsyncMock(return_value=None)
            
            metadata = await crawl4ai_wrapper.get_page_metadata("https://vnexpress.net")
            
            assert metadata['success'] is True
            assert metadata['title'] == 'Test Page Title'
            assert metadata['description'] == 'Test page description'
            assert metadata['status_code'] == 200


if __name__ == '__main__':
    pytest.main([__file__])