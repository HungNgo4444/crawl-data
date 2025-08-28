import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple
from urllib.parse import urljoin, urlparse

from crawl4ai import AsyncWebCrawler, CacheMode
from crawl4ai.extraction_strategy import JsonCssExtractionStrategy

from ..utils.crawl4ai_utils import Crawl4AIConfig, Crawl4AIRateLimiter, Crawl4AIErrorHandler
from ..utils.url_utils import URLValidator
from ..models.domain_config import DomainConfig

logger = logging.getLogger(__name__)


class Crawl4aiWrapper:
    """Wrapper for crawl4ai library integration"""
    
    def __init__(self, 
                 rate_limiter: Optional[Crawl4AIRateLimiter] = None,
                 max_retries: int = 3,
                 retry_delay: float = 2.0):
        self.browser_config = Crawl4AIConfig.create_browser_config(
            headless=True,
            browser_type="chromium",
            stealth_mode=True
        )
        
        self.rate_limiter = rate_limiter or Crawl4AIRateLimiter(
            requests_per_minute=30,
            burst_limit=5
        )
        
        self.url_validator = URLValidator()
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        # Link extraction strategy
        self.link_extraction_strategy = JsonCssExtractionStrategy(
            Crawl4AIConfig.create_link_extraction_strategy()["extraction_map"]
        )
    
    async def discover_urls_from_page(self, url: str, domain_config: DomainConfig) -> List[str]:
        """Use crawl4ai to discover URLs from homepage/category pages"""
        try:
            await self.rate_limiter.wait_if_needed()
            
            # Create crawler config for this domain
            crawler_config = Crawl4AIConfig.create_crawler_config(
                cache_mode=CacheMode.BYPASS,
                css_selector='a[href]',
                page_timeout=30000
            )
            
            discovered_urls = []
            
            async with AsyncWebCrawler(config=self.browser_config) as crawler:
                result = await crawler.arun(
                    url=url,
                    config=crawler_config,
                    extraction_strategy=self.link_extraction_strategy
                )
                
                if result.success and result.extracted_content:
                    urls = self._extract_urls_from_result(result, url, domain_config)
                    discovered_urls.extend(urls)
                    logger.info(f"Discovered {len(urls)} URLs from {url}")
                else:
                    logger.warning(f"Failed to discover URLs from {url}: {result.error_message}")
            
            return discovered_urls
            
        except Exception as e:
            logger.error(f"URL discovery error for '{url}': {e}")
            return []
    
    def _extract_urls_from_result(self, result, base_url: str, domain_config: DomainConfig) -> List[str]:
        """Extract and filter URLs from crawl result"""
        urls = []
        
        try:
            # Extract from structured data if available
            if hasattr(result, 'extracted_content') and result.extracted_content:
                extracted_data = result.extracted_content
                
                # Handle different extraction result formats
                if isinstance(extracted_data, dict):
                    # From JSON extraction strategy
                    for link_type in ['article_links', 'category_links']:
                        if link_type in extracted_data:
                            for link in extracted_data[link_type]:
                                if isinstance(link, dict) and 'url' in link:
                                    urls.append(link['url'])
                elif isinstance(extracted_data, list):
                    # From simple extraction
                    for item in extracted_data:
                        if isinstance(item, dict) and 'href' in item:
                            urls.append(item['href'])
            
            # Also extract from links in the result
            if hasattr(result, 'links') and result.links:
                if hasattr(result.links, 'internal') and result.links.internal:
                    for link in result.links.internal:
                        if hasattr(link, 'href'):
                            urls.append(link.href)
                        elif isinstance(link, str):
                            urls.append(link)
            
            # Normalize URLs
            normalized_urls = []
            for url in urls:
                if url:
                    # Convert relative URLs to absolute
                    absolute_url = urljoin(base_url, url.strip())
                    normalized_urls.append(absolute_url)
            
            # Filter URLs based on domain configuration
            filtered_urls = self._filter_urls_by_config(normalized_urls, domain_config)
            
            return list(set(filtered_urls))  # Remove duplicates
            
        except Exception as e:
            logger.error(f"URL extraction error: {e}")
            return []
    
    def _filter_urls_by_config(self, urls: List[str], domain_config: DomainConfig) -> List[str]:
        """Filter URLs based on domain configuration"""
        filtered_urls = []
        
        for url in urls:
            try:
                # Check if URL belongs to the domain
                parsed_url = urlparse(url)
                if not (domain_config.name in parsed_url.netloc):
                    continue
                
                # Apply include patterns
                if domain_config.url_patterns:
                    pattern_match = False
                    for pattern in domain_config.url_patterns:
                        import re
                        if re.search(pattern, url, re.IGNORECASE):
                            pattern_match = True
                            break
                    if not pattern_match:
                        continue
                
                # Apply exclude patterns
                if domain_config.exclude_patterns:
                    exclude_match = False
                    for pattern in domain_config.exclude_patterns:
                        if pattern in url:
                            exclude_match = True
                            break
                    if exclude_match:
                        continue
                
                # Use URL validator for additional filtering
                if self.url_validator.should_exclude_url(url):
                    continue
                
                # If we reach here, URL passed all filters
                filtered_urls.append(url)
                
            except Exception as e:
                logger.debug(f"URL filtering error for '{url}': {e}")
                continue
        
        return filtered_urls
    
    async def discover_urls_from_rss(self, rss_url: str, domain_config: DomainConfig) -> List[str]:
        """Discover URLs from RSS feeds"""
        try:
            import feedparser
            
            await self.rate_limiter.wait_if_needed()
            
            # Use crawl4ai to fetch RSS content (handles encoding better)
            crawler_config = Crawl4AIConfig.create_crawler_config(
                cache_mode=CacheMode.BYPASS,
                page_timeout=20000
            )
            
            async with AsyncWebCrawler(config=self.browser_config) as crawler:
                result = await crawler.arun(url=rss_url, config=crawler_config)
                
                if not result.success:
                    logger.warning(f"Failed to fetch RSS from {rss_url}")
                    return []
                
                # Parse RSS content
                feed = feedparser.parse(result.html)
                
                urls = []
                for entry in feed.entries:
                    if hasattr(entry, 'link') and entry.link:
                        urls.append(entry.link)
                
                # Filter URLs
                filtered_urls = self._filter_urls_by_config(urls, domain_config)
                
                logger.info(f"Discovered {len(filtered_urls)} URLs from RSS {rss_url}")
                return filtered_urls
                
        except Exception as e:
            logger.error(f"RSS discovery error for '{rss_url}': {e}")
            return []
    
    async def discover_urls_batch(self, urls: List[str], domain_config: DomainConfig) -> Dict[str, List[str]]:
        """Discover URLs from multiple sources concurrently"""
        results = {}
        
        # Create tasks for concurrent processing
        tasks = []
        for url in urls:
            if url.endswith('.rss') or url.endswith('.xml') or '/rss' in url:
                task = self.discover_urls_from_rss(url, domain_config)
            else:
                task = self.discover_urls_from_page(url, domain_config)
            
            tasks.append((url, task))
        
        # Execute tasks with proper error handling
        for source_url, task in tasks:
            try:
                discovered_urls = await task
                results[source_url] = discovered_urls
            except Exception as e:
                logger.error(f"Batch discovery error for '{source_url}': {e}")
                results[source_url] = []
        
        return results
    
    async def test_url_accessibility(self, url: str) -> Tuple[bool, Optional[str]]:
        """Test if URL is accessible and returns content"""
        try:
            await self.rate_limiter.wait_if_needed()
            
            crawler_config = Crawl4AIConfig.create_crawler_config(
                cache_mode=CacheMode.BYPASS,
                page_timeout=10000
            )
            
            async with AsyncWebCrawler(config=self.browser_config) as crawler:
                result = await crawler.arun(url=url, config=crawler_config)
                
                if result.success:
                    return True, None
                else:
                    return False, result.error_message
                    
        except Exception as e:
            error_category = Crawl4AIErrorHandler.get_error_category(e)
            return False, f"{error_category}: {str(e)}"
    
    async def get_page_metadata(self, url: str) -> Dict[str, Any]:
        """Get page metadata (title, description, etc.)"""
        try:
            await self.rate_limiter.wait_if_needed()
            
            crawler_config = Crawl4AIConfig.create_crawler_config(
                cache_mode=CacheMode.BYPASS,
                css_selector='title, meta[name="description"], meta[property="og:title"]',
                page_timeout=15000
            )
            
            async with AsyncWebCrawler(config=self.browser_config) as crawler:
                result = await crawler.arun(url=url, config=crawler_config)
                
                metadata = {
                    'url': url,
                    'success': result.success,
                    'title': '',
                    'description': '',
                    'status_code': getattr(result, 'status_code', 0)
                }
                
                if result.success and hasattr(result, 'metadata'):
                    metadata.update({
                        'title': result.metadata.get('title', ''),
                        'description': result.metadata.get('description', '')
                    })
                
                return metadata
                
        except Exception as e:
            logger.error(f"Metadata extraction error for '{url}': {e}")
            return {
                'url': url,
                'success': False,
                'error': str(e),
                'title': '',
                'description': ''
            }