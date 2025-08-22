"""
Sitemap Crawler - Comprehensive sitemap processing for Vietnamese news domains

This module implements comprehensive sitemap parsing with historical data extraction,
automatic detection, parallel processing, and date filtering capabilities.

Features:
- Automatic sitemap detection with parallel processing
- Historical data extraction with lastmod timestamps  
- Sitemap index handling with concurrent processing
- Date-range filtering for targeted content extraction
- Performance optimization and caching
- Vietnamese content prioritization
"""

import asyncio
import os
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urljoin, urlparse
import gzip
import json
import time
import re

import httpx
from dataclasses import dataclass

# Import Crawl4AI components
from crawl4ai import AsyncWebCrawler
import logging

@dataclass
class SitemapConfig:
    """Configuration for sitemap processing."""
    domain: str
    base_url: str
    sitemap_urls: Optional[List[str]] = None
    auto_detect: bool = True
    max_urls: int = 1000
    crawl_full_content: bool = True
    parallel_processing: bool = True
    max_concurrent_sitemaps: int = 5
    
@dataclass
class SitemapURL:
    """Represents a URL from sitemap with metadata."""
    url: str
    lastmod: Optional[datetime] = None
    changefreq: Optional[str] = None
    priority: Optional[float] = None
    url_image: Optional[str] = None
    crawled_content: Optional[str] = None
    crawl_metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.crawl_metadata is None:
            self.crawl_metadata = {}

@dataclass  
class SitemapCrawlResult:
    """Result from sitemap crawling operation."""
    domain: str
    success: bool
    discovered_urls: List[SitemapURL]
    total_sitemaps_processed: int
    total_urls_found: int
    execution_time: float
    error: Optional[str] = None

class SitemapCrawler:
    """
    Comprehensive sitemap crawler with Vietnamese news optimization.
    
    Provides automatic sitemap detection, parallel processing, historical data extraction,
    and intelligent filtering for Vietnamese news domains.
    """
    
    def __init__(
        self,
        logger = None,
        user_agent: str = None
    ):
        self.logger = logger or logging.getLogger("SITEMAP_CRAWLER")
        
        self.user_agent = user_agent or (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        # HTTP client for sitemap requests
        self.client = httpx.AsyncClient(
            timeout=60.0,
            headers={"User-Agent": self.user_agent},
            follow_redirects=True
        )
        
        # Crawl4AI client for full content extraction
        self.crawler = None  # Will be initialized when needed
    
    async def discover_sitemaps(self, config: SitemapConfig) -> List[str]:
        """
        Automatically discover sitemap URLs for a domain.
        
        Args:
            config: Sitemap configuration
            
        Returns:
            List of discovered sitemap URLs
        """
        discovered_sitemaps = []
        
        # Use provided sitemap URLs if available
        if config.sitemap_urls:
            self.logger.info(
                f"Using {len(config.sitemap_urls)} provided sitemap URLs for {config.domain}"
            )
            return config.sitemap_urls
        
        if not config.auto_detect:
            self.logger.warning(
                f"No sitemap URLs provided and auto-detect disabled for {config.domain}"
            )
            return []
        
        self.logger.info(f"Auto-discovering sitemaps for {config.domain}")
        
        # 1. Try common sitemap locations
        common_locations = [
            "/sitemap.xml",
            "/sitemap_index.xml", 
            "/sitemaps.xml",
            "/sitemap-index.xml",
            "/wp-sitemap.xml",  # WordPress
            "/sitemap/sitemap.xml"
        ]
        
        base_urls = [config.base_url.rstrip('/')]
        if not config.base_url.startswith('https://www.'):
            # Also try with www prefix
            parsed = urlparse(config.base_url)
            www_url = f"{parsed.scheme}://www.{parsed.netloc}"
            base_urls.append(www_url)
        
        for base_url in base_urls:
            for location in common_locations:
                sitemap_url = base_url + location
                if await self._check_sitemap_exists(sitemap_url):
                    discovered_sitemaps.append(sitemap_url)
                    self.logger.info(f"Found sitemap at {sitemap_url}")
        
        # 2. Check robots.txt for sitemap declarations
        robots_sitemaps = await self._discover_from_robots(config.base_url)
        for sitemap_url in robots_sitemaps:
            if sitemap_url not in discovered_sitemaps:
                discovered_sitemaps.append(sitemap_url)
                self.logger.info(f"Found sitemap in robots.txt: {sitemap_url}")
        
        self.logger.info(
            f"Sitemap discovery completed for {config.domain}: {len(discovered_sitemaps)} sitemaps found"
        )
        
        return discovered_sitemaps
    
    async def crawl_sitemaps(self, config: SitemapConfig) -> SitemapCrawlResult:
        """
        Crawl all sitemaps for a domain with comprehensive processing.
        
        Args:
            config: Sitemap configuration
            
        Returns:
            SitemapCrawlResult with all discovered URLs and metadata
        """
        start_time = time.time()
        
        try:
            # Discover sitemaps
            sitemap_urls = await self.discover_sitemaps(config)
            
            if not sitemap_urls:
                return SitemapCrawlResult(
                    domain=config.domain,
                    success=False,
                    discovered_urls=[],
                    total_sitemaps_processed=0,
                    total_urls_found=0,
                    execution_time=time.time() - start_time,
                    error="No sitemaps found"
                )
            
            self.logger.info(
                f"Starting sitemap crawl for {config.domain} with {len(sitemap_urls)} sitemaps"
            )
            
            # Process sitemaps
            if config.parallel_processing:
                urls = await self._process_sitemaps_parallel(sitemap_urls, config)
            else:
                urls = await self._process_sitemaps_sequential(sitemap_urls, config)
            
            # Apply filters
            filtered_urls = await self._apply_filters(urls, config)
            
            # Crawl full content if enabled
            if config.crawl_full_content and filtered_urls:
                self.logger.info(f"Crawling full content for {len(filtered_urls)} URLs from {config.domain}")
                filtered_urls = await self._crawl_full_content_for_urls(filtered_urls)
            
            execution_time = time.time() - start_time
            
            result = SitemapCrawlResult(
                domain=config.domain,
                success=True,
                discovered_urls=filtered_urls,
                total_sitemaps_processed=len(sitemap_urls),
                total_urls_found=len(urls),
                execution_time=execution_time
            )
            
            self.logger.info(
                f"Sitemap crawl completed for {config.domain}: {len(filtered_urls)} URLs processed"
            )
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = str(e)
            
            self.logger.error(f"Sitemap crawl failed for {config.domain}: {error_msg}")
            
            return SitemapCrawlResult(
                domain=config.domain,
                success=False,
                discovered_urls=[],
                total_sitemaps_processed=0,
                total_urls_found=0,
                execution_time=execution_time,
                error=error_msg
            )
    
    async def _process_sitemaps_parallel(
        self,
        sitemap_urls: List[str],
        config: SitemapConfig
    ) -> List[SitemapURL]:
        """Process multiple sitemaps in parallel."""
        
        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(config.max_concurrent_sitemaps)
        
        async def process_with_semaphore(sitemap_url: str):
            async with semaphore:
                return await self._process_single_sitemap(sitemap_url, config)
        
        # Execute all sitemaps concurrently
        tasks = [process_with_semaphore(url) for url in sitemap_urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Combine results
        all_urls = []
        
        for result in results:
            if isinstance(result, Exception):
                self.logger.error(f"Sitemap processing task failed: {str(result)}")
                continue
            
            all_urls.extend(result)
        
        return all_urls
    
    async def _process_sitemaps_sequential(
        self,
        sitemap_urls: List[str],
        config: SitemapConfig
    ) -> List[SitemapURL]:
        """Process sitemaps one by one."""
        
        all_urls = []
        
        for sitemap_url in sitemap_urls:
            try:
                urls = await self._process_single_sitemap(sitemap_url, config)
                all_urls.extend(urls)
            except Exception as e:
                self.logger.error(f"Failed to process sitemap {sitemap_url}: {str(e)}")
        
        return all_urls
    
    async def _process_single_sitemap(
        self,
        sitemap_url: str,
        config: SitemapConfig
    ) -> List[SitemapURL]:
        """Process a single sitemap file."""
        
        try:
            self.logger.debug(f"Processing sitemap: {sitemap_url}")
            
            # Fetch sitemap content
            response = await self.client.get(sitemap_url)
            response.raise_for_status()
            
            # Handle compressed sitemaps
            content = response.content
            if sitemap_url.endswith('.gz') or response.headers.get('content-encoding') == 'gzip':
                try:
                    content = gzip.decompress(content)
                except gzip.BadGzipFile:
                    # Not actually gzipped, use as-is
                    content = response.content
            
            # Parse XML
            root = ET.fromstring(content)
            
            # Determine sitemap type and process accordingly
            if 'sitemapindex' in root.tag or root.find('.//sitemap') is not None:
                urls = await self._process_sitemap_index(root, sitemap_url, config)
            else:
                urls = await self._process_regular_sitemap(root, sitemap_url, config)
            
            self.logger.debug(
                f"Processed sitemap {sitemap_url}: {len(urls)} URLs"
            )
            
            return urls
            
        except Exception as e:
            error_msg = str(e)
            self.logger.error(f"Error processing sitemap {sitemap_url}: {error_msg}")
            return []
    
    async def _process_sitemap_index(
        self,
        root: ET.Element,
        sitemap_url: str,
        config: SitemapConfig
    ) -> List[SitemapURL]:
        """Process a sitemap index file."""
        
        # Extract sub-sitemap URLs
        sub_sitemaps = []
        
        # Handle namespaced and non-namespaced elements
        sitemap_elements = root.findall('.//*')
        current_sitemap = None
        
        for elem in sitemap_elements:
            tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
            
            if tag == 'sitemap':
                current_sitemap = {}
            elif tag == 'loc' and current_sitemap is not None:
                current_sitemap['url'] = elem.text
            elif tag == 'lastmod' and current_sitemap is not None:
                current_sitemap['lastmod'] = await self._parse_datetime(elem.text)
                # Complete this sitemap entry
                sub_sitemaps.append(current_sitemap)
                current_sitemap = None
        
        self.logger.info(f"Sitemap index {sitemap_url} contains {len(sub_sitemaps)} sub-sitemaps")
        
        # Filter for news/article sitemaps only
        news_keywords = ['news', 'article', 'post', 'bai-viet', 'tin-tuc', '2025', '2024']
        image_keywords = ['image', 'media', 'files', 'styles', 'og_image']
        category_keywords = ['categories', 'topics', 'main', 'pages', 'home']
        
        filtered_sitemaps = []
        for sitemap in sub_sitemaps:
            sitemap_path = sitemap['url'].lower()
            
            # Skip image sitemaps
            if any(keyword in sitemap_path for keyword in image_keywords):
                self.logger.debug(f"Skipping image sitemap: {sitemap['url']}")
                continue
            
            # Skip category/page sitemaps unless they contain news keywords
            if any(keyword in sitemap_path for keyword in category_keywords):
                if not any(keyword in sitemap_path for keyword in news_keywords):
                    self.logger.debug(f"Skipping category sitemap: {sitemap['url']}")
                    continue
            
            # Prefer news/article sitemaps
            if any(keyword in sitemap_path for keyword in news_keywords):
                filtered_sitemaps.append(sitemap)
        
        # If no news sitemaps found, use first few general sitemaps
        if not filtered_sitemaps:
            filtered_sitemaps = sub_sitemaps[:3]
            
        self.logger.info(f"Using {len(filtered_sitemaps)} filtered sub-sitemaps for processing")
        
        # Process sub-sitemaps recursively (but limit depth to prevent infinite recursion)
        all_urls = []
        limit = min(len(filtered_sitemaps), config.max_concurrent_sitemaps)
        
        for sub_sitemap in filtered_sitemaps[:limit]:
            try:
                sub_urls = await self._process_single_sitemap(sub_sitemap['url'], config)
                all_urls.extend(sub_urls)
            except Exception as e:
                self.logger.warning(
                    f"Failed to process sub-sitemap {sub_sitemap['url']}: {str(e)}"
                )
        
        return all_urls
    
    async def _process_regular_sitemap(
        self,
        root: ET.Element,
        sitemap_url: str,
        config: SitemapConfig
    ) -> List[SitemapURL]:
        """Process a regular sitemap file."""
        
        urls = []
        
        # Handle namespaced and non-namespaced elements
        url_elements = root.findall('.//*')
        current_url = None
        
        for elem in url_elements:
            tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
            
            if tag == 'url':
                # Save previous URL if exists
                if current_url and current_url.get('url'):
                    sitemap_url_obj = SitemapURL(
                        url=current_url['url'],
                        lastmod=current_url.get('lastmod'),
                        changefreq=current_url.get('changefreq'),
                        priority=current_url.get('priority'),
                        url_image=current_url.get('url_image')
                    )
                    urls.append(sitemap_url_obj)
                
                # Start new URL
                current_url = {}
            elif tag == 'loc' and current_url is not None:
                current_url['url'] = elem.text
            elif tag == 'lastmod' and current_url is not None:
                current_url['lastmod'] = await self._parse_datetime(elem.text)
            elif tag == 'changefreq' and current_url is not None:
                current_url['changefreq'] = elem.text
            elif tag == 'priority' and current_url is not None:
                try:
                    current_url['priority'] = float(elem.text)
                except (ValueError, TypeError):
                    current_url['priority'] = None
            elif tag == 'image:loc' and current_url is not None:
                current_url['url_image'] = elem.text
        
        # Process any remaining URL after loop
        if current_url and current_url.get('url'):
            sitemap_url_obj = SitemapURL(
                url=current_url['url'],
                lastmod=current_url.get('lastmod'),
                changefreq=current_url.get('changefreq'),
                priority=current_url.get('priority'),
                url_image=current_url.get('url_image')
            )
            urls.append(sitemap_url_obj)
        
        return urls
    
    async def _check_sitemap_exists(self, sitemap_url: str) -> bool:
        """Check if a sitemap URL exists and is accessible."""
        try:
            response = await self.client.head(sitemap_url)
            return response.status_code == 200
        except:
            return False
    
    async def _discover_from_robots(self, base_url: str) -> List[str]:
        """Discover sitemaps from robots.txt."""
        sitemaps = []
        
        try:
            robots_url = urljoin(base_url.rstrip('/') + '/', 'robots.txt')
            response = await self.client.get(robots_url)
            
            if response.status_code == 200:
                content = response.text
                for line in content.splitlines():
                    line = line.strip()
                    if line.lower().startswith('sitemap:'):
                        sitemap_url = line.split(':', 1)[1].strip()
                        if sitemap_url:
                            sitemaps.append(sitemap_url)
        
        except Exception as e:
            self.logger.debug(f"Error reading robots.txt from {base_url}: {str(e)}")
        
        return sitemaps
    
    async def _apply_filters(self, urls: List[SitemapURL], config: SitemapConfig) -> List[SitemapURL]:
        """Apply various filters to URLs."""
        filtered_urls = []
        
        for url_obj in urls:
            # URL limit
            if len(filtered_urls) >= config.max_urls:
                break
            
            filtered_urls.append(url_obj)
        
        return filtered_urls
    
    async def _crawl_full_content_for_urls(self, urls: List[SitemapURL]) -> List[SitemapURL]:
        """Crawl full content for sitemap URLs using Crawl4AI."""
        if not urls:
            return urls
            
        # Initialize crawler if needed
        if self.crawler is None:
            self.crawler = AsyncWebCrawler(verbose=False)
        
        self.logger.info(f"Starting full content crawl for {len(urls)} URLs")
        
        # Process URLs concurrently but with limit
        semaphore = asyncio.Semaphore(3)  # Limit concurrent crawls
        
        async def crawl_single_url(url_obj: SitemapURL) -> SitemapURL:
            async with semaphore:
                try:
                    self.logger.debug(f"Crawling content for: {url_obj.url}")
                    
                    # Crawl the page content
                    result = await self.crawler.arun(
                        url=url_obj.url,
                        word_count_threshold=10,
                        bypass_cache=False
                    )
                    
                    if result and result.success:
                        url_obj.crawled_content = result.cleaned_html or result.markdown
                        
                        # Extract image from crawled content
                        if url_obj.crawled_content:
                            url_obj.url_image = await self._extract_image_from_content(
                                url_obj.crawled_content, url_obj.url
                            )
                        
                        url_obj.crawl_metadata = {
                            "success": True,
                            "status_code": getattr(result, 'status_code', None),
                            "word_count": len(url_obj.crawled_content.split()) if url_obj.crawled_content else 0,
                            "extraction_time": getattr(result, 'response_time', None),
                            "crawl_timestamp": datetime.utcnow().isoformat(),
                            "image_extracted": bool(url_obj.url_image)
                        }
                        self.logger.debug(
                            f"Successfully crawled {len(url_obj.crawled_content)} chars from {url_obj.url} (image: {bool(url_obj.url_image)})"
                        )
                    else:
                        url_obj.crawl_metadata = {
                            "success": False, 
                            "error": "Crawl failed",
                            "crawl_timestamp": datetime.utcnow().isoformat()
                        }
                        self.logger.warning(f"Failed to crawl content from {url_obj.url}")
                        
                except Exception as e:
                    url_obj.crawl_metadata = {
                        "success": False,
                        "error": str(e),
                        "crawl_timestamp": datetime.utcnow().isoformat()
                    }
                    self.logger.error(f"Error crawling {url_obj.url}: {str(e)}")
                
                return url_obj
        
        # Execute all crawling tasks
        tasks = [crawl_single_url(url_obj) for url_obj in urls]
        crawled_urls = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions
        valid_urls = []
        for result in crawled_urls:
            if isinstance(result, Exception):
                self.logger.error(f"Crawling task failed: {str(result)}")
                continue
            valid_urls.append(result)
        
        success_count = sum(1 for url_obj in valid_urls if url_obj.crawl_metadata.get("success", False))
        self.logger.info(f"Content crawling completed: {success_count}/{len(valid_urls)} successful")
        
        return valid_urls
    
    async def _extract_image_from_content(self, content: str, base_url: str) -> Optional[str]:
        """Extract image URL from HTML content."""
        if not content:
            return None
        
        img_pattern = r'<img[^>]+src=["\']([^"\'>]+)["\']'
        img_matches = re.findall(img_pattern, content, re.IGNORECASE)
        
        if img_matches:
            img_url = img_matches[0]
            if not img_url.startswith('http'):
                img_url = urljoin(base_url, img_url)
            return img_url
        
        return None
    
    async def _parse_datetime(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse various datetime formats from sitemaps."""
        if not date_str:
            return None
        
        try:
            # Remove timezone info for simple parsing
            clean_date = date_str.replace('Z', '').split('+')[0].split('-')[0:3]
            
            # Try ISO format
            if 'T' in date_str:
                return datetime.fromisoformat(date_str.replace('Z', ''))
            
            # Try date-only format
            if len(clean_date) >= 3:
                date_part = '-'.join(clean_date[:3])
                return datetime.fromisoformat(date_part)
                
        except Exception as e:
            self.logger.debug(f"Date parsing failed for '{date_str}': {str(e)}")
        
        return None
    
    async def close(self):
        """Clean up resources."""
        await self.client.aclose()
        if self.crawler:
            await self.crawler.close()
        print("Sitemap crawler closed")