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
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urljoin, urlparse
import gzip
import hashlib
import json
import time
import re
from pathlib import Path

import aiofiles
import httpx
from dataclasses import dataclass

# Import Crawl4AI components
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'crawl4ai-main'))

from crawl4ai.async_url_seeder import AsyncUrlSeeder
from crawl4ai.async_configs import SeedingConfig
from crawl4ai.async_logger import AsyncLogger

@dataclass
class SitemapConfig:
    """Configuration for sitemap processing."""
    domain: str
    base_url: str
    sitemap_urls: Optional[List[str]] = None
    auto_detect: bool = True
    max_urls: int = 50000
    date_filter_start: Optional[datetime] = None  
    date_filter_end: Optional[datetime] = None
    vietnamese_optimization: bool = True
    parallel_processing: bool = True
    max_concurrent_sitemaps: int = 10
    cache_ttl_days: int = 7
    
@dataclass
class SitemapURL:
    """Represents a URL from sitemap with metadata."""
    url: str
    lastmod: Optional[datetime] = None
    changefreq: Optional[str] = None
    priority: Optional[float] = None
    sitemap_source: str = ""
    vietnamese_score: float = 0.0
    content_category: Optional[str] = None

@dataclass
class SitemapInfo:
    """Information about a sitemap file."""
    url: str
    type: str  # "sitemap" or "sitemapindex"
    lastmod: Optional[datetime] = None
    total_urls: int = 0
    processing_time: float = 0.0
    success: bool = True
    error: Optional[str] = None

@dataclass  
class SitemapCrawlResult:
    """Result from sitemap crawling operation."""
    domain: str
    success: bool
    discovered_urls: List[SitemapURL]
    sitemap_info: List[SitemapInfo]
    total_sitemaps_processed: int
    total_urls_found: int
    filtered_urls_count: int
    execution_time: float
    cache_used: bool = False
    error: Optional[str] = None
    performance_metrics: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.performance_metrics is None:
            self.performance_metrics = {}

class SitemapCrawler:
    """
    Comprehensive sitemap crawler with Vietnamese news optimization.
    
    Provides automatic sitemap detection, parallel processing, historical data extraction,
    and intelligent filtering for Vietnamese news domains.
    """
    
    def __init__(
        self,
        logger: Optional[AsyncLogger] = None,
        cache_dir: Optional[Path] = None,
        user_agent: str = None
    ):
        self.logger = logger or AsyncLogger()
        self.cache_dir = cache_dir or Path.home() / ".crawl4ai" / "sitemap_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
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
        
        # Initialize URL Seeder for advanced processing
        self.url_seeder = AsyncUrlSeeder(logger=self.logger)
        
        # Vietnamese content patterns for URL scoring
        self.vietnamese_url_patterns = [
            "tin-tuc", "bao-chi", "thoi-su", "kinh-te", "xa-hoi", "the-thao",
            "phap-luat", "giao-duc", "suc-khoe", "cong-nghe", "van-hoa",
            "du-lich", "oto-xe-may", "bat-dong-san", "giai-tri", "am-nhac"
        ]
        
        # Common Vietnamese news URL indicators
        self.vietnamese_indicators = [
            ".vn/", "vietnam", "saigon", "hanoi", "danang", "hcm", "hochiminh"
        ]
        
        # Performance tracking
        self.performance_stats = {
            "total_sitemaps_processed": 0,
            "total_urls_discovered": 0,
            "average_processing_time": 0.0,
            "cache_hit_rate": 0.0,
            "vietnamese_urls_found": 0,
            "last_processing_time": None
        }
    
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
                f"Using {len(config.sitemap_urls)} provided sitemap URLs for {config.domain}",
                tag="SITEMAP_CRAWLER"
            )
            return config.sitemap_urls
        
        if not config.auto_detect:
            self.logger.warning(
                f"No sitemap URLs provided and auto-detect disabled for {config.domain}",
                tag="SITEMAP_CRAWLER"
            )
            return []
        
        self.logger.info(f"Auto-discovering sitemaps for {config.domain}", tag="SITEMAP_CRAWLER")
        
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
                    self.logger.info(f"Found sitemap at {sitemap_url}", tag="SITEMAP_CRAWLER")
        
        # 2. Check robots.txt for sitemap declarations
        robots_sitemaps = await self._discover_from_robots(config.base_url)
        for sitemap_url in robots_sitemaps:
            if sitemap_url not in discovered_sitemaps:
                discovered_sitemaps.append(sitemap_url)
                self.logger.info(f"Found sitemap in robots.txt: {sitemap_url}", tag="SITEMAP_CRAWLER")
        
        self.logger.info(
            f"Sitemap discovery completed for {config.domain}: {len(discovered_sitemaps)} sitemaps found",
            tag="SITEMAP_CRAWLER"
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
                    sitemap_info=[],
                    total_sitemaps_processed=0,
                    total_urls_found=0,
                    filtered_urls_count=0,
                    execution_time=time.time() - start_time,
                    error="No sitemaps found"
                )
            
            self.logger.info(
                f"Starting sitemap crawl for {config.domain} with {len(sitemap_urls)} sitemaps",
                tag="SITEMAP_CRAWLER"
            )
            
            # Check cache first
            cache_key = self._generate_cache_key(config, sitemap_urls)
            cached_result = await self._get_cached_result(cache_key, config.cache_ttl_days)
            
            if cached_result:
                self.logger.info(f"Using cached sitemap results for {config.domain}", tag="SITEMAP_CRAWLER")
                cached_result.cache_used = True
                cached_result.execution_time = time.time() - start_time
                return cached_result
            
            # Process sitemaps
            if config.parallel_processing:
                urls, sitemap_info = await self._process_sitemaps_parallel(sitemap_urls, config)
            else:
                urls, sitemap_info = await self._process_sitemaps_sequential(sitemap_urls, config)
            
            # Apply filters
            filtered_urls = await self._apply_filters(urls, config)
            
            # Apply Vietnamese scoring if enabled
            if config.vietnamese_optimization:
                filtered_urls = await self._apply_vietnamese_scoring(filtered_urls)
            
            execution_time = time.time() - start_time
            
            result = SitemapCrawlResult(
                domain=config.domain,
                success=True,
                discovered_urls=filtered_urls,
                sitemap_info=sitemap_info,
                total_sitemaps_processed=len(sitemap_info),
                total_urls_found=len(urls),
                filtered_urls_count=len(filtered_urls),
                execution_time=execution_time,
                performance_metrics=self._calculate_performance_metrics(sitemap_info, execution_time)
            )
            
            # Cache the result
            await self._cache_result(cache_key, result)
            
            # Update performance stats
            self._update_performance_stats(result)
            
            self.logger.info(
                f"Sitemap crawl completed for {config.domain}: {len(filtered_urls)} URLs from {len(sitemap_info)} sitemaps",
                tag="SITEMAP_CRAWLER"
            )
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = str(e)
            
            self.logger.error(f"Sitemap crawl failed for {config.domain}: {error_msg}", tag="SITEMAP_CRAWLER")
            
            return SitemapCrawlResult(
                domain=config.domain,
                success=False,
                discovered_urls=[],
                sitemap_info=[],
                total_sitemaps_processed=0,
                total_urls_found=0,
                filtered_urls_count=0,
                execution_time=execution_time,
                error=error_msg
            )
    
    async def _process_sitemaps_parallel(
        self,
        sitemap_urls: List[str],
        config: SitemapConfig
    ) -> Tuple[List[SitemapURL], List[SitemapInfo]]:
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
        all_sitemap_info = []
        
        for result in results:
            if isinstance(result, Exception):
                self.logger.error(f"Sitemap processing task failed: {str(result)}", tag="SITEMAP_CRAWLER")
                continue
            
            urls, info = result
            all_urls.extend(urls)
            all_sitemap_info.append(info)
        
        return all_urls, all_sitemap_info
    
    async def _process_sitemaps_sequential(
        self,
        sitemap_urls: List[str],
        config: SitemapConfig
    ) -> Tuple[List[SitemapURL], List[SitemapInfo]]:
        """Process sitemaps one by one."""
        
        all_urls = []
        all_sitemap_info = []
        
        for sitemap_url in sitemap_urls:
            try:
                urls, info = await self._process_single_sitemap(sitemap_url, config)
                all_urls.extend(urls)
                all_sitemap_info.append(info)
            except Exception as e:
                self.logger.error(f"Failed to process sitemap {sitemap_url}: {str(e)}", tag="SITEMAP_CRAWLER")
                
                # Add failed sitemap info
                all_sitemap_info.append(SitemapInfo(
                    url=sitemap_url,
                    type="unknown",
                    success=False,
                    error=str(e)
                ))
        
        return all_urls, all_sitemap_info
    
    async def _process_single_sitemap(
        self,
        sitemap_url: str,
        config: SitemapConfig
    ) -> Tuple[List[SitemapURL], SitemapInfo]:
        """Process a single sitemap file."""
        start_time = time.time()
        
        try:
            self.logger.debug(f"Processing sitemap: {sitemap_url}", tag="SITEMAP_CRAWLER")
            
            # Fetch sitemap content
            response = await self.client.get(sitemap_url)
            response.raise_for_status()
            
            # Handle compressed sitemaps
            content = response.content
            if sitemap_url.endswith('.gz') or response.headers.get('content-encoding') == 'gzip':
                content = gzip.decompress(content)
            
            # Parse XML
            root = ET.fromstring(content)
            
            # Determine sitemap type and process accordingly
            if 'sitemapindex' in root.tag:
                urls, sitemap_type = await self._process_sitemap_index(root, sitemap_url, config)
            else:
                urls, sitemap_type = await self._process_regular_sitemap(root, sitemap_url, config)
            
            processing_time = time.time() - start_time
            
            sitemap_info = SitemapInfo(
                url=sitemap_url,
                type=sitemap_type,
                total_urls=len(urls),
                processing_time=processing_time,
                success=True
            )
            
            self.logger.debug(
                f"Processed sitemap {sitemap_url}: {len(urls)} URLs in {processing_time:.2f}s",
                tag="SITEMAP_CRAWLER"
            )
            
            return urls, sitemap_info
            
        except Exception as e:
            processing_time = time.time() - start_time
            error_msg = str(e)
            
            self.logger.error(f"Error processing sitemap {sitemap_url}: {error_msg}", tag="SITEMAP_CRAWLER")
            
            sitemap_info = SitemapInfo(
                url=sitemap_url,
                type="unknown",
                processing_time=processing_time,
                success=False,
                error=error_msg
            )
            
            return [], sitemap_info
    
    async def _process_sitemap_index(
        self,
        root: ET.Element,
        sitemap_url: str,
        config: SitemapConfig
    ) -> Tuple[List[SitemapURL], str]:
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
        
        self.logger.info(f"Sitemap index {sitemap_url} contains {len(sub_sitemaps)} sub-sitemaps", tag="SITEMAP_CRAWLER")
        
        # Process sub-sitemaps recursively (but limit depth to prevent infinite recursion)
        all_urls = []
        if len(sub_sitemaps) <= config.max_concurrent_sitemaps:
            # Process all sub-sitemaps
            for sub_sitemap in sub_sitemaps:
                try:
                    sub_urls, _ = await self._process_single_sitemap(sub_sitemap['url'], config)
                    all_urls.extend(sub_urls)
                except Exception as e:
                    self.logger.warning(
                        f"Failed to process sub-sitemap {sub_sitemap['url']}: {str(e)}",
                        tag="SITEMAP_CRAWLER"
                    )
        else:
            self.logger.warning(
                f"Too many sub-sitemaps ({len(sub_sitemaps)}), processing first {config.max_concurrent_sitemaps}",
                tag="SITEMAP_CRAWLER"
            )
            for sub_sitemap in sub_sitemaps[:config.max_concurrent_sitemaps]:
                try:
                    sub_urls, _ = await self._process_single_sitemap(sub_sitemap['url'], config)
                    all_urls.extend(sub_urls)
                except Exception as e:
                    self.logger.warning(
                        f"Failed to process sub-sitemap {sub_sitemap['url']}: {str(e)}",
                        tag="SITEMAP_CRAWLER"
                    )
        
        return all_urls, "sitemapindex"
    
    async def _process_regular_sitemap(
        self,
        root: ET.Element,
        sitemap_url: str,
        config: SitemapConfig
    ) -> Tuple[List[SitemapURL], str]:
        """Process a regular sitemap file."""
        
        urls = []
        
        # Handle namespaced and non-namespaced elements
        url_elements = root.findall('.//*')
        current_url = None
        
        for elem in url_elements:
            tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
            
            if tag == 'url':
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
                
                # URL entry is complete
                if current_url.get('url'):
                    sitemap_url_obj = SitemapURL(
                        url=current_url['url'],
                        lastmod=current_url.get('lastmod'),
                        changefreq=current_url.get('changefreq'),
                        priority=current_url.get('priority'),
                        sitemap_source=sitemap_url
                    )
                    urls.append(sitemap_url_obj)
                
                current_url = None
        
        return urls, "sitemap"
    
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
            self.logger.debug(f"Error reading robots.txt from {base_url}: {str(e)}", tag="SITEMAP_CRAWLER")
        
        return sitemaps
    
    async def _apply_filters(self, urls: List[SitemapURL], config: SitemapConfig) -> List[SitemapURL]:
        """Apply various filters to URLs."""
        filtered_urls = []
        
        for url_obj in urls:
            # Date filter
            if config.date_filter_start or config.date_filter_end:
                if url_obj.lastmod:
                    if config.date_filter_start and url_obj.lastmod < config.date_filter_start:
                        continue
                    if config.date_filter_end and url_obj.lastmod > config.date_filter_end:
                        continue
            
            # URL limit
            if len(filtered_urls) >= config.max_urls:
                break
            
            filtered_urls.append(url_obj)
        
        return filtered_urls
    
    async def _apply_vietnamese_scoring(self, urls: List[SitemapURL]) -> List[SitemapURL]:
        """Apply Vietnamese content scoring to URLs."""
        
        for url_obj in urls:
            score = 0.0
            url_lower = url_obj.url.lower()
            
            # Check for Vietnamese URL patterns
            for pattern in self.vietnamese_url_patterns:
                if pattern in url_lower:
                    score += 0.2
            
            # Check for Vietnamese domain indicators
            for indicator in self.vietnamese_indicators:
                if indicator in url_lower:
                    score += 0.3
                    break
            
            # Check for Vietnamese news categories
            if any(cat in url_lower for cat in ['tin-tuc', 'thoi-su', 'kinh-te', 'xa-hoi']):
                score += 0.4
            
            # Check for date patterns in URL (Vietnamese news often includes dates)
            if re.search(r'/\d{4}/\d{2}/', url_lower) or re.search(r'/\d{6}/', url_lower):
                score += 0.1
            
            url_obj.vietnamese_score = min(score, 1.0)
            
            # Determine content category
            url_obj.content_category = self._categorize_url(url_obj.url)
        
        # Sort by Vietnamese score (descending)
        urls.sort(key=lambda x: x.vietnamese_score, reverse=True)
        
        return urls
    
    def _categorize_url(self, url: str) -> str:
        """Categorize URL based on path patterns."""
        url_lower = url.lower()
        
        categories = {
            'news': ['tin-tuc', 'thoi-su', 'bao-chi'],
            'economy': ['kinh-te', 'tai-chinh', 'chung-khoan'], 
            'society': ['xa-hoi', 'doi-song', 'giao-duc'],
            'sports': ['the-thao', 'bong-da', 'tennis'],
            'technology': ['cong-nghe', 'khoa-hoc', 'internet'],
            'entertainment': ['giai-tri', 'am-nhac', 'phim'],
            'health': ['suc-khoe', 'y-te', 'dinh-duong'],
            'travel': ['du-lich', 'am-thuc']
        }
        
        for category, patterns in categories.items():
            if any(pattern in url_lower for pattern in patterns):
                return category
        
        return 'general'
    
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
            self.logger.debug(f"Date parsing failed for '{date_str}': {str(e)}", tag="SITEMAP_CRAWLER")
        
        return None
    
    def _generate_cache_key(self, config: SitemapConfig, sitemap_urls: List[str]) -> str:
        """Generate cache key for sitemap results."""
        key_data = {
            'domain': config.domain,
            'sitemap_urls': sorted(sitemap_urls),
            'max_urls': config.max_urls,
            'date_filter_start': config.date_filter_start.isoformat() if config.date_filter_start else None,
            'date_filter_end': config.date_filter_end.isoformat() if config.date_filter_end else None,
            'vietnamese_optimization': config.vietnamese_optimization
        }
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_str.encode()).hexdigest()
    
    async def _get_cached_result(self, cache_key: str, ttl_days: int) -> Optional[SitemapCrawlResult]:
        """Get cached sitemap result if still valid."""
        cache_file = self.cache_dir / f"{cache_key}.json"
        
        try:
            if cache_file.exists():
                # Check if cache is still valid
                file_age = time.time() - cache_file.stat().st_mtime
                if file_age < (ttl_days * 24 * 3600):
                    async with aiofiles.open(cache_file, 'r', encoding='utf-8') as f:
                        content = await f.read()
                        data = json.loads(content)
                        
                    # Reconstruct result object
                    return self._deserialize_result(data)
        except Exception as e:
            self.logger.debug(f"Error reading cache: {str(e)}", tag="SITEMAP_CRAWLER")
        
        return None
    
    async def _cache_result(self, cache_key: str, result: SitemapCrawlResult):
        """Cache sitemap result."""
        cache_file = self.cache_dir / f"{cache_key}.json"
        
        try:
            data = self._serialize_result(result)
            async with aiofiles.open(cache_file, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(data, ensure_ascii=False, indent=2))
        except Exception as e:
            self.logger.debug(f"Error writing cache: {str(e)}", tag="SITEMAP_CRAWLER")
    
    def _serialize_result(self, result: SitemapCrawlResult) -> Dict[str, Any]:
        """Serialize result for caching."""
        return {
            'domain': result.domain,
            'success': result.success,
            'discovered_urls': [
                {
                    'url': url.url,
                    'lastmod': url.lastmod.isoformat() if url.lastmod else None,
                    'changefreq': url.changefreq,
                    'priority': url.priority,
                    'sitemap_source': url.sitemap_source,
                    'vietnamese_score': url.vietnamese_score,
                    'content_category': url.content_category
                } for url in result.discovered_urls
            ],
            'sitemap_info': [
                {
                    'url': info.url,
                    'type': info.type,
                    'lastmod': info.lastmod.isoformat() if info.lastmod else None,
                    'total_urls': info.total_urls,
                    'processing_time': info.processing_time,
                    'success': info.success,
                    'error': info.error
                } for info in result.sitemap_info
            ],
            'total_sitemaps_processed': result.total_sitemaps_processed,
            'total_urls_found': result.total_urls_found,
            'filtered_urls_count': result.filtered_urls_count,
            'error': result.error,
            'performance_metrics': result.performance_metrics
        }
    
    def _deserialize_result(self, data: Dict[str, Any]) -> SitemapCrawlResult:
        """Deserialize cached result."""
        discovered_urls = []
        for url_data in data.get('discovered_urls', []):
            discovered_urls.append(SitemapURL(
                url=url_data['url'],
                lastmod=datetime.fromisoformat(url_data['lastmod']) if url_data.get('lastmod') else None,
                changefreq=url_data.get('changefreq'),
                priority=url_data.get('priority'),
                sitemap_source=url_data.get('sitemap_source', ''),
                vietnamese_score=url_data.get('vietnamese_score', 0.0),
                content_category=url_data.get('content_category')
            ))
        
        sitemap_info = []
        for info_data in data.get('sitemap_info', []):
            sitemap_info.append(SitemapInfo(
                url=info_data['url'],
                type=info_data['type'],
                lastmod=datetime.fromisoformat(info_data['lastmod']) if info_data.get('lastmod') else None,
                total_urls=info_data.get('total_urls', 0),
                processing_time=info_data.get('processing_time', 0.0),
                success=info_data.get('success', True),
                error=info_data.get('error')
            ))
        
        return SitemapCrawlResult(
            domain=data['domain'],
            success=data['success'],
            discovered_urls=discovered_urls,
            sitemap_info=sitemap_info,
            total_sitemaps_processed=data.get('total_sitemaps_processed', 0),
            total_urls_found=data.get('total_urls_found', 0),
            filtered_urls_count=data.get('filtered_urls_count', 0),
            execution_time=0.0,  # Will be updated when returned
            error=data.get('error'),
            performance_metrics=data.get('performance_metrics', {})
        )
    
    def _calculate_performance_metrics(self, sitemap_info: List[SitemapInfo], total_time: float) -> Dict[str, Any]:
        """Calculate performance metrics for the crawl."""
        successful_sitemaps = [info for info in sitemap_info if info.success]
        
        return {
            'total_processing_time': total_time,
            'successful_sitemaps': len(successful_sitemaps),
            'failed_sitemaps': len(sitemap_info) - len(successful_sitemaps),
            'average_sitemap_processing_time': sum(info.processing_time for info in successful_sitemaps) / len(successful_sitemaps) if successful_sitemaps else 0,
            'urls_per_second': sum(info.total_urls for info in successful_sitemaps) / total_time if total_time > 0 else 0
        }
    
    def _update_performance_stats(self, result: SitemapCrawlResult):
        """Update internal performance statistics."""
        self.performance_stats['total_sitemaps_processed'] += result.total_sitemaps_processed
        self.performance_stats['total_urls_discovered'] += result.total_urls_found
        
        # Update average processing time
        current_avg = self.performance_stats['average_processing_time']
        if current_avg == 0:
            self.performance_stats['average_processing_time'] = result.execution_time
        else:
            self.performance_stats['average_processing_time'] = (current_avg + result.execution_time) / 2
        
        # Count Vietnamese URLs
        vietnamese_urls = sum(1 for url in result.discovered_urls if url.vietnamese_score > 0.3)
        self.performance_stats['vietnamese_urls_found'] += vietnamese_urls
        
        # Update cache hit rate (simplified)
        if result.cache_used:
            self.performance_stats['cache_hit_rate'] = min(self.performance_stats['cache_hit_rate'] + 0.1, 1.0)
        else:
            self.performance_stats['cache_hit_rate'] = max(self.performance_stats['cache_hit_rate'] - 0.05, 0.0)
        
        self.performance_stats['last_processing_time'] = datetime.utcnow().isoformat()
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get current performance statistics."""
        return self.performance_stats.copy()
    
    async def close(self):
        """Clean up resources."""
        await self.client.aclose()
        if self.url_seeder:
            await self.url_seeder.close()
        self.logger.info("Sitemap crawler closed", tag="SITEMAP_CRAWLER")