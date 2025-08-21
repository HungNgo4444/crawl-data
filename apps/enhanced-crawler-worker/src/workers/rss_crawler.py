"""
RSS Feed Crawler - Universal RSS feed processing with Crawl4AI integration

This module implements real-time RSS feed monitoring and URL extraction
with full content crawling using Crawl4AI for comprehensive data extraction.

Features:
- Real-time RSS feed monitoring with configurable intervals (5-15 minutes)
- RSS feed parsing with publication date extraction  
- Universal content crawling (no language filtering)
- Full content extraction using Crawl4AI for all discovered URLs
- RSS feed health checking and error recovery
- Performance metrics tracking for RSS-specific operations
"""

import asyncio
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set
from urllib.parse import urljoin, urlparse
import hashlib
import json
import time

import aiofiles
import httpx
from dataclasses import dataclass

# Import Crawl4AI components
from crawl4ai import AsyncWebCrawler
import logging

@dataclass 
class RSSFeedConfig:
    """Configuration for RSS feed processing."""
    url: str
    title: Optional[str] = None
    check_interval: int = 900  # 15 minutes default
    max_items: int = 100
    crawl_full_content: bool = True  # Enable full content crawling with Crawl4AI
    last_checked: Optional[datetime] = None
    health_status: str = "unknown"  # unknown, healthy, degraded, failed

@dataclass
class RSSItem:
    """Represents a single RSS item."""
    title: str
    link: str
    description: Optional[str] = None
    pub_date: Optional[datetime] = None
    guid: Optional[str] = None
    categories: List[str] = None
    author: Optional[str] = None
    content: Optional[str] = None
    crawled_content: Optional[str] = None  # Full content from Crawl4AI
    crawl_metadata: Dict[str, Any] = None  # Metadata from Crawl4AI extraction
    
    def __post_init__(self):
        if self.categories is None:
            self.categories = []
        if self.crawl_metadata is None:
            self.crawl_metadata = {}

@dataclass
class RSSCrawlResult:
    """Result from RSS crawling operation."""
    feed_url: str
    success: bool
    items: List[RSSItem]
    total_items: int
    new_items: int
    execution_time: float
    error: Optional[str] = None
    feed_metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.feed_metadata is None:
            self.feed_metadata = {}

class RSSCrawler:
    """
    Universal RSS feed crawler with Crawl4AI integration.
    
    Features real-time monitoring, full content extraction, and health checking
    for comprehensive data crawling from RSS feed URLs.
    """
    
    def __init__(
        self,
        logger = None,
        cache_dir: Optional[str] = None,
        user_agent: str = None
    ):
        self.logger = logger or logging.getLogger("RSS_CRAWLER")
        self.cache_dir = cache_dir or os.path.expanduser("~/.crawl4ai/rss_cache")
        os.makedirs(self.cache_dir, exist_ok=True)
        
        self.user_agent = user_agent or (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        # HTTP client for RSS requests
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers={"User-Agent": self.user_agent},
            follow_redirects=True
        )
        
        # Crawl4AI client for full content extraction  
        self.crawler = None  # Will be initialized when needed
        
        # Feed configurations and state
        self.feed_configs: Dict[str, RSSFeedConfig] = {}
        self.feed_state: Dict[str, Dict[str, Any]] = {}
        
        # Performance tracking
        self.performance_metrics = {
            "total_feeds_processed": 0,
            "successful_fetches": 0,
            "failed_fetches": 0,
            "total_items_discovered": 0,
            "total_content_crawled": 0,
            "crawl_success_rate": 0.0,
            "average_processing_time": 0.0,
            "last_processing_time": None
        }
    
    async def add_feed(self, feed_config: RSSFeedConfig) -> bool:
        """
        Add an RSS feed to monitoring list.
        
        Args:
            feed_config: RSS feed configuration
            
        Returns:
            True if feed was added successfully
        """
        try:
            # Validate feed by fetching it once
            result = await self.crawl_single_feed(feed_config.url, validate_only=True)
            
            if result.success:
                self.feed_configs[feed_config.url] = feed_config
                self.feed_state[feed_config.url] = {
                    "last_etag": None,
                    "last_modified": None,
                    "seen_guids": set(),
                    "consecutive_failures": 0,
                    "last_successful_fetch": datetime.utcnow()
                }
                
                self.logger.info(f"Added RSS feed: {feed_config.url} (title: {feed_config.title})")
                return True
            else:
                self.logger.error(
                    f"Failed to validate RSS feed {feed_config.url}: {result.error}",
                    tag="RSS_CRAWLER"
                )
                return False
                
        except Exception as e:
            self.logger.error(f"Error adding RSS feed {feed_config.url}: {str(e)}", tag="RSS_CRAWLER")
            return False
    
    async def crawl_single_feed(
        self,
        feed_url: str,
        validate_only: bool = False,
        force_refresh: bool = False
    ) -> RSSCrawlResult:
        """
        Crawl a single RSS feed and extract items.
        
        Args:
            feed_url: RSS feed URL
            validate_only: Only validate the feed, don't process items
            force_refresh: Ignore cache and fetch fresh content
            
        Returns:
            RSSCrawlResult with discovered items
        """
        start_time = time.time()
        
        try:
            # Get cached state for this feed
            state = self.feed_state.get(feed_url, {})
            
            # Prepare conditional headers for efficient fetching
            headers = {}
            if not force_refresh:
                if state.get("last_etag"):
                    headers["If-None-Match"] = state["last_etag"]
                if state.get("last_modified"):
                    headers["If-Modified-Since"] = state["last_modified"]
            
            self.logger.debug(f"Fetching RSS feed: {feed_url}", tag="RSS_CRAWLER")
            
            # Fetch RSS content
            response = await self.client.get(feed_url, headers=headers)
            
            # Handle 304 Not Modified
            if response.status_code == 304:
                execution_time = time.time() - start_time
                self.logger.info(f"RSS feed not modified: {feed_url}", tag="RSS_CRAWLER")
                
                return RSSCrawlResult(
                    feed_url=feed_url,
                    success=True,
                    items=[],
                    total_items=0,
                    new_items=0,
                    execution_time=execution_time,
                    feed_metadata={"status": "not_modified"}
                )
            
            response.raise_for_status()
            
            # Update cache headers
            if feed_url in self.feed_state:
                self.feed_state[feed_url]["last_etag"] = response.headers.get("etag")
                self.feed_state[feed_url]["last_modified"] = response.headers.get("last-modified")
            
            # Parse RSS content
            rss_content = response.text
            items = await self._parse_rss_content(rss_content, feed_url)
            
            if validate_only:
                execution_time = time.time() - start_time
                return RSSCrawlResult(
                    feed_url=feed_url,
                    success=True,
                    items=[],
                    total_items=len(items),
                    new_items=0,
                    execution_time=execution_time,
                    feed_metadata={"validation": "passed"}
                )
            
            # Filter for new items
            seen_guids = state.get("seen_guids", set())
            new_items = []
            
            for item in items:
                item_id = item.guid or item.link
                if item_id not in seen_guids:
                    new_items.append(item)
                    seen_guids.add(item_id)
            
            # Crawl full content for new items if enabled
            feed_config = self.feed_configs.get(feed_url)
            if feed_config and feed_config.crawl_full_content and new_items:
                self.logger.info(f"Crawling full content for {len(new_items)} new items from {feed_url}", tag="RSS_CRAWLER")
                new_items = await self._crawl_full_content_for_items(new_items)
            
            # Update seen GUIDs (keep only recent ones to prevent memory growth)
            if len(seen_guids) > 10000:
                # Keep only most recent 5000 GUIDs
                recent_guids = set(list(seen_guids)[-5000:])
                seen_guids = recent_guids
            
            if feed_url in self.feed_state:
                self.feed_state[feed_url]["seen_guids"] = seen_guids
                self.feed_state[feed_url]["consecutive_failures"] = 0
                self.feed_state[feed_url]["last_successful_fetch"] = datetime.utcnow()
            
            execution_time = time.time() - start_time
            
            # Extract feed metadata
            feed_metadata = await self._extract_feed_metadata(rss_content)
            
            self.logger.info(
                f"RSS crawl completed for {feed_url}: {len(new_items)} new items from {len(items)} total",
                tag="RSS_CRAWLER"
            )
            
            # Update performance metrics  
            crawled_count = sum(1 for item in new_items if item.crawled_content)
            self._update_performance_metrics(len(items), len(new_items), crawled_count, execution_time, True)
            
            return RSSCrawlResult(
                feed_url=feed_url,
                success=True,
                items=new_items,
                total_items=len(items),
                new_items=len(new_items),
                execution_time=execution_time,
                feed_metadata=feed_metadata
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = str(e)
            
            # Update failure tracking
            if feed_url in self.feed_state:
                self.feed_state[feed_url]["consecutive_failures"] += 1
            
            self.logger.error(f"RSS crawl failed for {feed_url}: {error_msg}", tag="RSS_CRAWLER")
            
            # Update performance metrics
            self._update_performance_metrics(0, 0, 0, execution_time, False)
            
            return RSSCrawlResult(
                feed_url=feed_url,
                success=False,
                items=[],
                total_items=0,
                new_items=0,
                execution_time=execution_time,
                error=error_msg
            )
    
    async def crawl_all_feeds(
        self,
        force_refresh: bool = False,
        parallel_limit: int = 5
    ) -> Dict[str, RSSCrawlResult]:
        """
        Crawl all configured RSS feeds in parallel.
        
        Args:
            force_refresh: Ignore cache for all feeds
            parallel_limit: Maximum concurrent feed processing
            
        Returns:
            Dictionary mapping feed URLs to crawl results
        """
        if not self.feed_configs:
            self.logger.warning("No RSS feeds configured", tag="RSS_CRAWLER")
            return {}
        
        self.logger.info(
            f"Starting RSS crawl for {len(self.feed_configs)} feeds (parallel={parallel_limit})",
            tag="RSS_CRAWLER"
        )
        
        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(parallel_limit)
        
        async def crawl_with_semaphore(feed_url: str) -> Tuple[str, RSSCrawlResult]:
            async with semaphore:
                result = await self.crawl_single_feed(feed_url, force_refresh=force_refresh)
                return feed_url, result
        
        # Execute all feeds concurrently
        tasks = [crawl_with_semaphore(feed_url) for feed_url in self.feed_configs.keys()]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        feed_results = {}
        successful_feeds = 0
        total_new_items = 0
        
        for result in results:
            if isinstance(result, Exception):
                self.logger.error(f"Feed crawl task failed: {str(result)}", tag="RSS_CRAWLER")
                continue
            
            feed_url, crawl_result = result
            feed_results[feed_url] = crawl_result
            
            if crawl_result.success:
                successful_feeds += 1
                total_new_items += crawl_result.new_items
        
        self.logger.info(
            f"RSS crawl batch completed: {successful_feeds}/{len(self.feed_configs)} successful, "
            f"{total_new_items} total new items",
            tag="RSS_CRAWLER"
        )
        
        return feed_results
    
    async def start_monitoring(
        self,
        check_interval: int = 900,  # 15 minutes
        parallel_limit: int = 5
    ):
        """
        Start continuous RSS feed monitoring.
        
        Args:
            check_interval: Interval between checks in seconds
            parallel_limit: Maximum concurrent feeds to process
        """
        self.logger.info(
            f"Starting RSS monitoring with {check_interval}s interval for {len(self.feed_configs)} feeds",
            tag="RSS_CRAWLER"
        )
        
        while True:
            try:
                # Crawl all feeds
                results = await self.crawl_all_feeds(parallel_limit=parallel_limit)
                
                # Health check and feed management
                await self._perform_health_checks(results)
                
                # Wait for next interval
                self.logger.debug(f"RSS monitoring cycle complete, sleeping for {check_interval}s", tag="RSS_CRAWLER")
                await asyncio.sleep(check_interval)
                
            except KeyboardInterrupt:
                self.logger.info("RSS monitoring stopped by user", tag="RSS_CRAWLER")
                break
            except Exception as e:
                self.logger.error(f"Error in RSS monitoring loop: {str(e)}", tag="RSS_CRAWLER")
                await asyncio.sleep(60)  # Wait before retry
    
    async def _parse_rss_content(self, rss_content: str, feed_url: str) -> List[RSSItem]:
        """Parse RSS XML content into RSSItem objects."""
        items = []
        
        try:
            # Parse XML
            root = ET.fromstring(rss_content)
            
            # Handle RSS 2.0 format
            if root.tag == 'rss':
                channel = root.find('channel')
                if channel is not None:
                    items_elements = channel.findall('item')
                else:
                    items_elements = []
            
            # Handle Atom format
            elif root.tag.endswith('feed'):
                items_elements = root.findall('.//{http://www.w3.org/2005/Atom}entry')
            
            # Handle other formats
            else:
                items_elements = root.findall('.//item')
            
            for item_elem in items_elements:
                item = await self._parse_rss_item(item_elem, feed_url)
                if item:
                    items.append(item)
                    
        except ET.ParseError as e:
            self.logger.error(f"XML parsing error for {feed_url}: {str(e)}", tag="RSS_CRAWLER")
        except Exception as e:
            self.logger.error(f"Error parsing RSS content for {feed_url}: {str(e)}", tag="RSS_CRAWLER")
        
        return items
    
    async def _parse_rss_item(self, item_elem: ET.Element, feed_url: str) -> Optional[RSSItem]:
        """Parse a single RSS item element."""
        try:
            # Extract basic fields
            title_elem = item_elem.find('title')
            title = title_elem.text.strip() if title_elem is not None and title_elem.text else ""
            
            link_elem = item_elem.find('link')
            link = link_elem.text.strip() if link_elem is not None and link_elem.text else ""
            
            # Make link absolute
            if link and not link.startswith('http'):
                base_url = f"{urlparse(feed_url).scheme}://{urlparse(feed_url).netloc}"
                link = urljoin(base_url, link)
            
            if not title or not link:
                return None
            
            # Extract description
            desc_elem = item_elem.find('description') 
            description = desc_elem.text.strip() if desc_elem is not None and desc_elem.text else None
            
            # Extract publication date
            pub_date = None
            pub_date_elem = item_elem.find('pubDate')
            if pub_date_elem is not None and pub_date_elem.text:
                pub_date = await self._parse_date(pub_date_elem.text)
            
            # Extract GUID
            guid_elem = item_elem.find('guid')
            guid = guid_elem.text.strip() if guid_elem is not None and guid_elem.text else None
            
            # Extract categories
            categories = []
            category_elems = item_elem.findall('category')
            for cat_elem in category_elems:
                if cat_elem.text:
                    categories.append(cat_elem.text.strip())
            
            # Extract author
            author_elem = item_elem.find('author') or item_elem.find('dc:creator', {'dc': 'http://purl.org/dc/elements/1.1/'})
            author = author_elem.text.strip() if author_elem is not None and author_elem.text else None
            
            # Extract content
            content_elem = item_elem.find('content:encoded', {'content': 'http://purl.org/rss/1.0/modules/content/'})
            content = content_elem.text.strip() if content_elem is not None and content_elem.text else None
            
            # Create RSS item
            rss_item = RSSItem(
                title=title,
                link=link,
                description=description,
                pub_date=pub_date,
                guid=guid,
                categories=categories,
                author=author,
                content=content
            )
            
            return rss_item
            
        except Exception as e:
            self.logger.error(f"Error parsing RSS item: {str(e)}", tag="RSS_CRAWLER")
            return None
    
    async def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse various RSS date formats."""
        import email.utils
        
        try:
            # Try RFC 2822 format (common in RSS)
            parsed_time = email.utils.parsedate_tz(date_str)
            if parsed_time:
                timestamp = email.utils.mktime_tz(parsed_time)
                return datetime.fromtimestamp(timestamp)
            
            # Try ISO format
            if 'T' in date_str:
                # Remove timezone info for simple parsing
                clean_date = date_str.split('+')[0].split('-')[0:3]
                clean_date = '-'.join(clean_date[:3]) + 'T' + date_str.split('T')[1].split('+')[0]
                return datetime.fromisoformat(clean_date.replace('Z', ''))
            
        except Exception as e:
            self.logger.debug(f"Date parsing failed for '{date_str}': {str(e)}", tag="RSS_CRAWLER")
        
        return None
    
    async def _crawl_full_content_for_items(self, items: List[RSSItem]) -> List[RSSItem]:
        """Crawl full content for RSS items using Crawl4AI."""
        if not items:
            return items
            
        # Initialize crawler if needed
        if self.crawler is None:
            self.crawler = AsyncWebCrawler(verbose=False)
            await self.crawler.awarmup()
        
        self.logger.info(f"Starting full content crawl for {len(items)} items", tag="RSS_CRAWLER")
        
        # Process items concurrently but with limit
        semaphore = asyncio.Semaphore(3)  # Limit concurrent crawls
        
        async def crawl_single_item(item: RSSItem) -> RSSItem:
            async with semaphore:
                try:
                    self.logger.debug(f"Crawling content for: {item.link}", tag="RSS_CRAWLER")
                    
                    # Crawl the page content
                    result = await self.crawler.arun(
                        url=item.link,
                        word_count_threshold=10,
                        bypass_cache=False
                    )
                    
                    if result and result.success:
                        item.crawled_content = result.cleaned_html or result.markdown
                        item.crawl_metadata = {
                            "success": True,
                            "status_code": getattr(result, 'status_code', None),
                            "word_count": len(item.crawled_content.split()) if item.crawled_content else 0,
                            "extraction_time": getattr(result, 'response_time', None),
                            "crawl_timestamp": datetime.utcnow().isoformat()
                        }
                        self.logger.debug(f"Successfully crawled {len(item.crawled_content)} chars from {item.link}", tag="RSS_CRAWLER")
                    else:
                        item.crawl_metadata = {
                            "success": False, 
                            "error": "Crawl failed",
                            "crawl_timestamp": datetime.utcnow().isoformat()
                        }
                        self.logger.warning(f"Failed to crawl content from {item.link}", tag="RSS_CRAWLER")
                        
                except Exception as e:
                    item.crawl_metadata = {
                        "success": False,
                        "error": str(e),
                        "crawl_timestamp": datetime.utcnow().isoformat()
                    }
                    self.logger.error(f"Error crawling {item.link}: {str(e)}", tag="RSS_CRAWLER")
                
                return item
        
        # Execute all crawling tasks
        tasks = [crawl_single_item(item) for item in items]
        crawled_items = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions
        valid_items = []
        for result in crawled_items:
            if isinstance(result, Exception):
                self.logger.error(f"Crawling task failed: {str(result)}", tag="RSS_CRAWLER")
                continue
            valid_items.append(result)
        
        success_count = sum(1 for item in valid_items if item.crawl_metadata.get("success", False))
        self.logger.info(f"Content crawling completed: {success_count}/{len(valid_items)} successful", tag="RSS_CRAWLER")
        
        return valid_items
    
    # Vietnamese scoring removed - now crawls all content universally
    
    async def _extract_feed_metadata(self, rss_content: str) -> Dict[str, Any]:
        """Extract metadata from RSS feed."""
        metadata = {}
        
        try:
            root = ET.fromstring(rss_content)
            
            if root.tag == 'rss':
                channel = root.find('channel')
                if channel is not None:
                    # Basic channel info
                    title_elem = channel.find('title')
                    if title_elem is not None:
                        metadata['title'] = title_elem.text
                    
                    desc_elem = channel.find('description')
                    if desc_elem is not None:
                        metadata['description'] = desc_elem.text
                    
                    link_elem = channel.find('link')
                    if link_elem is not None:
                        metadata['link'] = link_elem.text
                    
                    # Language
                    lang_elem = channel.find('language')
                    if lang_elem is not None:
                        metadata['language'] = lang_elem.text
                    
                    # Last build date
                    build_date_elem = channel.find('lastBuildDate')
                    if build_date_elem is not None:
                        metadata['last_build_date'] = build_date_elem.text
        
        except Exception as e:
            self.logger.debug(f"Error extracting feed metadata: {str(e)}", tag="RSS_CRAWLER")
        
        return metadata
    
    async def _perform_health_checks(self, results: Dict[str, RSSCrawlResult]):
        """Perform health checks on RSS feeds based on recent results."""
        for feed_url, result in results.items():
            if feed_url not in self.feed_configs:
                continue
            
            config = self.feed_configs[feed_url]
            state = self.feed_state.get(feed_url, {})
            
            if result.success:
                config.health_status = "healthy"
                config.last_checked = datetime.utcnow()
            else:
                consecutive_failures = state.get("consecutive_failures", 0)
                if consecutive_failures < 3:
                    config.health_status = "degraded"
                else:
                    config.health_status = "failed"
            
            # Log health status changes
            self.logger.debug(
                f"RSS feed health check - {feed_url}: {config.health_status} "
                f"(failures: {state.get('consecutive_failures', 0)})",
                tag="RSS_CRAWLER"
            )
    
    def _update_performance_metrics(self, total_items: int, new_items: int, crawled_items: int, execution_time: float, success: bool):
        """Update performance tracking metrics."""
        self.performance_metrics["total_feeds_processed"] += 1
        
        if success:
            self.performance_metrics["successful_fetches"] += 1
        else:
            self.performance_metrics["failed_fetches"] += 1
        
        self.performance_metrics["total_items_discovered"] += total_items
        self.performance_metrics["total_content_crawled"] += crawled_items
        
        # Update crawl success rate
        if new_items > 0:
            current_rate = self.performance_metrics["crawl_success_rate"] 
            self.performance_metrics["crawl_success_rate"] = (current_rate + (crawled_items / new_items)) / 2
        
        # Update average processing time
        current_avg = self.performance_metrics["average_processing_time"]
        total_processed = self.performance_metrics["total_feeds_processed"]
        
        if total_processed > 1:
            self.performance_metrics["average_processing_time"] = (
                (current_avg * (total_processed - 1) + execution_time) / total_processed
            )
        else:
            self.performance_metrics["average_processing_time"] = execution_time
        
        self.performance_metrics["last_processing_time"] = datetime.utcnow().isoformat()
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics."""
        return self.performance_metrics.copy()
    
    def get_feed_health_status(self) -> Dict[str, Dict[str, Any]]:
        """Get health status for all configured feeds."""
        status = {}
        
        for feed_url, config in self.feed_configs.items():
            state = self.feed_state.get(feed_url, {})
            status[feed_url] = {
                "title": config.title,
                "health_status": config.health_status,
                "last_checked": config.last_checked.isoformat() if config.last_checked else None,
                "consecutive_failures": state.get("consecutive_failures", 0),
                "last_successful_fetch": state.get("last_successful_fetch").isoformat() if state.get("last_successful_fetch") else None
            }
        
        return status
    
    async def close(self):
        """Clean up resources."""
        await self.client.aclose()
        if self.crawler:
            await self.crawler.aclose()
        print("RSS crawler closed")