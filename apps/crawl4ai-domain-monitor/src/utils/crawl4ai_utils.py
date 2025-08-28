import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class Crawl4AIConfig:
    """Configuration utilities for crawl4ai integration"""
    
    @staticmethod
    def create_browser_config(
        headless: bool = True,
        browser_type: str = "chromium", 
        stealth_mode: bool = True,
        viewport_width: int = 1920,
        viewport_height: int = 1080,
        user_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create optimized browser config for Vietnamese news sites"""
        
        # Vietnamese-optimized user agent if none provided
        if not user_agent:
            user_agent = (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
            )
        
        extra_args = [
            '--lang=vi-VN',
            '--accept-lang=vi-VN,vi,en-US,en',
            '--no-sandbox',
            '--disable-dev-shm-usage',
            '--disable-gpu',
            '--disable-background-timer-throttling',
            '--disable-backgrounding-occluded-windows',
            '--disable-renderer-backgrounding'
        ]
        
        if stealth_mode:
            extra_args.extend([
                '--disable-blink-features=AutomationControlled',
                '--no-first-run',
                '--disable-default-apps',
                '--disable-features=TranslateUI',
                '--disable-ipc-flooding-protection'
            ])
        
        return {
            'headless': headless,
            'browser_type': browser_type,
            'viewport_width': viewport_width,
            'viewport_height': viewport_height,
            'user_agent': user_agent,
            'accept_downloads': False,
            'java_script_enabled': True,
            'ignore_https_errors': True,
            'extra_args': extra_args
        }
    
    @staticmethod
    def create_crawler_config(
        cache_mode: str = "bypass",
        word_count_threshold: int = 10,
        extraction_strategy: Optional[str] = None,
        css_selector: Optional[str] = None,
        wait_for: Optional[str] = None,
        page_timeout: int = 30000,
        **kwargs
    ) -> Dict[str, Any]:
        """Create crawler run config for URL discovery"""
        
        config = {
            'cache_mode': cache_mode,
            'word_count_threshold': word_count_threshold,
            'page_timeout': page_timeout,
            'only_text': False,
            'remove_overlay_elements': True,
            'simulate_user': True,
            'override_navigator': True
        }
        
        # Add CSS selector for link extraction if provided
        if css_selector:
            config['css_selector'] = css_selector
        else:
            # Default selector for Vietnamese news sites
            config['css_selector'] = 'a[href*="http"]'
        
        # Wait condition for dynamic content
        if wait_for:
            config['wait_for'] = wait_for
        
        return config
    
    @staticmethod
    def get_vietnamese_news_selectors() -> Dict[str, str]:
        """Get CSS selectors optimized for Vietnamese news sites"""
        return {
            # Common article link selectors
            'article_links': (
                'a[href*=".html"], '
                'a[href*="/tin-tuc/"], '
                'a[href*="/bai-viet/"], '
                'a[class*="title"], '
                'a[class*="headline"], '
                '.article-title a, '
                '.news-title a, '
                '.story-title a'
            ),
            
            # Homepage navigation links
            'navigation_links': (
                'nav a[href], '
                '.menu a[href], '
                '.navigation a[href], '
                'header a[href]'
            ),
            
            # Category page links
            'category_links': (
                '.category-list a, '
                '.section-list a, '
                'a[href*="/category/"], '
                'a[href*="/chuyen-muc/"]'
            ),
            
            # Exclude selectors
            'exclude_links': (
                'a[href*="/tag/"], '
                'a[href*="/search/"], '
                'a[href*="/login"], '
                'a[href*="/register"], '
                'a[href*="javascript:"], '
                'a[href^="#"], '
                'a[href*=".jpg"], '
                'a[href*=".png"], '
                'a[href*=".pdf"]'
            )
        }
    
    @staticmethod
    def create_link_extraction_strategy() -> Dict[str, Any]:
        """Create JSON extraction strategy for links"""
        selectors = Crawl4AIConfig.get_vietnamese_news_selectors()
        
        return {
            "name": "vietnamese_news_links",
            "schema": {
                "type": "object",
                "properties": {
                    "article_links": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "url": {"type": "string"},
                                "title": {"type": "string"},
                                "text": {"type": "string"}
                            }
                        }
                    },
                    "category_links": {
                        "type": "array", 
                        "items": {
                            "type": "object",
                            "properties": {
                                "url": {"type": "string"},
                                "title": {"type": "string"},
                                "text": {"type": "string"}
                            }
                        }
                    }
                }
            },
            "extraction_map": {
                "article_links": {
                    "selector": selectors['article_links'],
                    "fields": {
                        "url": {"attribute": "href"},
                        "title": {"attribute": "title"},
                        "text": {"text": True}
                    }
                },
                "category_links": {
                    "selector": selectors['category_links'],
                    "fields": {
                        "url": {"attribute": "href"},
                        "title": {"attribute": "title"},
                        "text": {"text": True}
                    }
                }
            }
        }


class Crawl4AIRateLimiter:
    """Rate limiting for crawl4ai requests"""
    
    def __init__(self, requests_per_minute: int = 30, burst_limit: int = 5):
        self.requests_per_minute = requests_per_minute
        self.burst_limit = burst_limit
        self.request_times = []
        self.burst_count = 0
    
    async def wait_if_needed(self):
        """Wait if rate limit would be exceeded"""
        import asyncio
        from datetime import datetime, timedelta
        
        now = datetime.now()
        
        # Remove old requests (older than 1 minute)
        cutoff = now - timedelta(minutes=1)
        self.request_times = [t for t in self.request_times if t > cutoff]
        
        # Check rate limit
        if len(self.request_times) >= self.requests_per_minute:
            wait_time = 60.0 / self.requests_per_minute
            logger.info(f"Rate limit reached, waiting {wait_time:.1f} seconds")
            await asyncio.sleep(wait_time)
        
        # Check burst limit
        recent_cutoff = now - timedelta(seconds=10)
        recent_requests = [t for t in self.request_times if t > recent_cutoff]
        
        if len(recent_requests) >= self.burst_limit:
            wait_time = 2.0
            logger.info(f"Burst limit reached, waiting {wait_time} seconds")
            await asyncio.sleep(wait_time)
        
        # Record this request
        self.request_times.append(now)


class Crawl4AIErrorHandler:
    """Error handling utilities for crawl4ai operations"""
    
    RETRYABLE_ERRORS = [
        "TimeoutError",
        "NetworkError", 
        "ConnectionError",
        "ProtocolError"
    ]
    
    @staticmethod
    def is_retryable_error(error: Exception) -> bool:
        """Check if error is retryable"""
        error_name = type(error).__name__
        error_msg = str(error).lower()
        
        if error_name in Crawl4AIErrorHandler.RETRYABLE_ERRORS:
            return True
        
        # Check error message for retryable patterns
        retryable_patterns = [
            "timeout", "connection", "network", "dns", 
            "ssl", "certificate", "handshake"
        ]
        
        return any(pattern in error_msg for pattern in retryable_patterns)
    
    @staticmethod
    def get_error_category(error: Exception) -> str:
        """Categorize error for logging and handling"""
        error_name = type(error).__name__
        error_msg = str(error).lower()
        
        if "timeout" in error_msg or error_name == "TimeoutError":
            return "timeout"
        elif any(term in error_msg for term in ["connection", "network", "dns"]):
            return "network"
        elif any(term in error_msg for term in ["ssl", "certificate"]):
            return "ssl"
        elif "permission" in error_msg or "access" in error_msg:
            return "access_denied"
        elif "not found" in error_msg or "404" in error_msg:
            return "not_found"
        else:
            return "unknown"