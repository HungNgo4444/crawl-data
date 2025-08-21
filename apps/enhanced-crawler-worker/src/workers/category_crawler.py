"""
Category Crawler - Deep crawling of category/section URLs for Vietnamese news domains

This module implements intelligent category page traversal with pagination support,
Vietnamese content detection, and depth-limited exploration for news categories.

Features:
- Pagination traversal trong category pages
- Content section discovery với Vietnamese patterns  
- Category-specific URL extraction và filtering
- Intelligent depth control cho category exploration
- Performance monitoring và optimization
"""

import asyncio
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urljoin, urlparse, parse_qs, urlunparse, urlencode
import json
import time
from pathlib import Path

import httpx
from dataclasses import dataclass

# Import Crawl4AI components
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'crawl4ai-main'))

from crawl4ai.deep_crawling.bfs_strategy import BFSDeepCrawlStrategy
from crawl4ai.deep_crawling.filters import FilterChain, URLPatternFilter, ContentRelevanceFilter
from crawl4ai.deep_crawling.scorers import KeywordRelevanceScorer, CompositeScorer
from crawl4ai.async_logger import AsyncLogger

@dataclass
class CategoryConfig:
    """Configuration for category crawling."""
    domain: str
    category_urls: List[str]
    max_depth: int = 3
    max_pages_per_category: int = 100
    max_concurrent: int = 5
    vietnamese_optimization: bool = True
    follow_pagination: bool = True
    extract_subcategories: bool = True
    content_keywords: List[str] = None
    exclude_patterns: List[str] = None
    
    def __post_init__(self):
        if self.content_keywords is None:
            self.content_keywords = [
                "tin tức", "báo chí", "thời sự", "kinh tế", "xã hội", 
                "thể thao", "pháp luật", "giáo dục", "sức khỏe", "công nghệ"
            ]
        if self.exclude_patterns is None:
            self.exclude_patterns = [
                "*/search/*", "*/tag/*", "*/author/*", "*/archive/*", 
                "*/admin/*", "*/login/*", "*/register/*"
            ]

@dataclass
class CategoryURL:
    """Represents a URL discovered from category crawling."""
    url: str
    category_source: str
    discovered_depth: int = 0
    page_number: Optional[int] = None
    subcategory: Optional[str] = None
    vietnamese_score: float = 0.0
    relevance_score: float = 0.0
    discovered_at: datetime = None
    
    def __post_init__(self):
        if self.discovered_at is None:
            self.discovered_at = datetime.utcnow()

@dataclass
class CategoryCrawlResult:
    """Result from category crawling operation."""
    domain: str
    success: bool
    discovered_urls: List[CategoryURL]
    categories_processed: List[Dict[str, Any]]
    total_pages_crawled: int
    pagination_discovered: int
    subcategories_found: int
    execution_time: float
    error: Optional[str] = None
    performance_metrics: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.performance_metrics is None:
            self.performance_metrics = {}

class CategoryCrawler:
    """
    Intelligent category crawler for Vietnamese news domains.
    
    Specializes in exploring news category pages with pagination support,
    Vietnamese content detection, and hierarchical category discovery.
    """
    
    def __init__(
        self,
        logger: Optional[AsyncLogger] = None,
        user_agent: str = None
    ):
        self.logger = logger or AsyncLogger()
        self.user_agent = user_agent or (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        # HTTP client for category requests
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers={"User-Agent": self.user_agent},
            follow_redirects=True
        )
        
        # Vietnamese category patterns
        self.vietnamese_category_patterns = [
            # News categories
            "tin-tuc", "thoi-su", "bao-chi", "quan-su", "chinh-tri",
            # Economy categories  
            "kinh-te", "tai-chinh", "chung-khoan", "bat-dong-san", "doanh-nghiep",
            # Society categories
            "xa-hoi", "doi-song", "giao-duc", "suc-khoe", "phap-luat",
            # Sports categories
            "the-thao", "bong-da", "tennis", "quan-vot", "boi-loi",
            # Technology categories
            "cong-nghe", "khoa-hoc", "internet", "di-dong", "may-tinh",
            # Entertainment categories
            "giai-tri", "am-nhac", "phim", "sao", "thoi-trang",
            # Lifestyle categories
            "du-lich", "am-thuc", "o-to", "xe-may", "nha-dat"
        ]
        
        # Pagination patterns commonly used in Vietnamese websites
        self.pagination_patterns = [
            # Vietnamese pagination
            r'trang\s*(\d+)',
            r'page\s*(\d+)', 
            r'p(\d+)',
            # Numeric pagination
            r'\/(\d+)\/',
            r'[?&]page=(\d+)',
            r'[?&]p=(\d+)',
            r'[?&]trang=(\d+)',
            # Next/Previous patterns
            r'(tiếp\s*theo|next)',
            r'(trang\s*sau|sau)',
            r'(trang\s*trước|trước|previous)',
        ]
        
        # Performance tracking
        self.performance_stats = {
            "total_categories_processed": 0,
            "total_urls_discovered": 0,
            "total_pages_crawled": 0,
            "pagination_success_rate": 0.0,
            "subcategory_discovery_rate": 0.0,
            "vietnamese_content_rate": 0.0,
            "average_processing_time": 0.0,
            "last_crawl_time": None
        }
    
    async def crawl_categories(self, config: CategoryConfig) -> CategoryCrawlResult:
        """
        Crawl multiple category URLs with intelligent exploration.
        
        Args:
            config: Category crawling configuration
            
        Returns:
            CategoryCrawlResult with discovered URLs and metrics
        """
        start_time = time.time()
        
        try:
            self.logger.info(
                f"Starting category crawl for {config.domain} with {len(config.category_urls)} categories",
                tag="CATEGORY_CRAWLER"
            )
            
            # Process categories in parallel with concurrency limit
            semaphore = asyncio.Semaphore(config.max_concurrent)
            
            async def crawl_single_category_with_semaphore(category_url: str):
                async with semaphore:
                    return await self._crawl_single_category(category_url, config)
            
            # Execute all category crawls concurrently
            tasks = [crawl_single_category_with_semaphore(url) for url in config.category_urls]
            category_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            all_urls = []
            categories_processed = []
            total_pages = 0
            pagination_found = 0
            subcategories_found = 0
            
            for i, result in enumerate(category_results):
                if isinstance(result, Exception):
                    self.logger.error(
                        f"Category crawl failed for {config.category_urls[i]}: {str(result)}",
                        tag="CATEGORY_CRAWLER"
                    )
                    categories_processed.append({
                        "url": config.category_urls[i],
                        "success": False,
                        "error": str(result)
                    })
                    continue
                
                urls, category_info = result
                all_urls.extend(urls)
                categories_processed.append(category_info)
                
                if category_info["success"]:
                    total_pages += category_info.get("pages_crawled", 0)
                    pagination_found += category_info.get("pagination_pages", 0)
                    subcategories_found += category_info.get("subcategories_found", 0)
            
            # Apply Vietnamese scoring if enabled
            if config.vietnamese_optimization:
                all_urls = await self._apply_vietnamese_scoring(all_urls, config)
            
            # Remove duplicates while preserving best scores
            unique_urls = await self._deduplicate_urls(all_urls)
            
            # Sort by relevance scores
            unique_urls.sort(key=lambda x: (x.vietnamese_score, x.relevance_score), reverse=True)
            
            execution_time = time.time() - start_time
            
            result = CategoryCrawlResult(
                domain=config.domain,
                success=True,
                discovered_urls=unique_urls,
                categories_processed=categories_processed,
                total_pages_crawled=total_pages,
                pagination_discovered=pagination_found,
                subcategories_found=subcategories_found,
                execution_time=execution_time,
                performance_metrics=self._calculate_performance_metrics(
                    categories_processed, unique_urls, execution_time
                )
            )
            
            self._update_performance_stats(result)
            
            self.logger.info(
                f"Category crawl completed for {config.domain}: "
                f"{len(unique_urls)} URLs from {len(categories_processed)} categories "
                f"in {execution_time:.2f}s",
                tag="CATEGORY_CRAWLER"
            )
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = str(e)
            
            self.logger.error(
                f"Category crawl failed for {config.domain}: {error_msg}",
                tag="CATEGORY_CRAWLER"
            )
            
            return CategoryCrawlResult(
                domain=config.domain,
                success=False,
                discovered_urls=[],
                categories_processed=[],
                total_pages_crawled=0,
                pagination_discovered=0,
                subcategories_found=0,
                execution_time=execution_time,
                error=error_msg
            )
    
    async def _crawl_single_category(
        self,
        category_url: str,
        config: CategoryConfig
    ) -> Tuple[List[CategoryURL], Dict[str, Any]]:
        """
        Crawl a single category with pagination and subcategory discovery.
        
        Args:
            category_url: URL of the category to crawl
            config: Crawling configuration
            
        Returns:
            Tuple of (discovered URLs, category info)
        """
        start_time = time.time()
        category_info = {
            "url": category_url,
            "success": False,
            "pages_crawled": 0,
            "pagination_pages": 0,
            "subcategories_found": 0,
            "urls_discovered": 0,
            "error": None
        }
        
        try:
            self.logger.debug(f"Crawling category: {category_url}", tag="CATEGORY_CRAWLER")
            
            discovered_urls = []
            visited_pages = set()
            pages_to_visit = [(category_url, 0)]  # (url, depth)
            
            while pages_to_visit and len(discovered_urls) < config.max_pages_per_category:
                current_url, depth = pages_to_visit.pop(0)
                
                if current_url in visited_pages or depth > config.max_depth:
                    continue
                
                visited_pages.add(current_url)
                
                # Crawl current page
                page_urls, page_info = await self._crawl_category_page(
                    current_url, category_url, depth, config
                )
                
                discovered_urls.extend(page_urls)
                category_info["pages_crawled"] += 1
                
                # Discover pagination links
                if config.follow_pagination and depth == 0:  # Only follow pagination from main category page
                    pagination_urls = await self._discover_pagination(current_url, config)
                    for page_url in pagination_urls:
                        if page_url not in visited_pages:
                            pages_to_visit.append((page_url, depth))
                            category_info["pagination_pages"] += 1
                
                # Discover subcategories
                if config.extract_subcategories and depth < config.max_depth:
                    subcategory_urls = await self._discover_subcategories(current_url, config)
                    for subcat_url in subcategory_urls:
                        if subcat_url not in visited_pages:
                            pages_to_visit.append((subcat_url, depth + 1))
                            category_info["subcategories_found"] += 1
                
                # Prevent infinite loops
                if category_info["pages_crawled"] > config.max_pages_per_category:
                    break
            
            category_info["success"] = True
            category_info["urls_discovered"] = len(discovered_urls)
            category_info["processing_time"] = time.time() - start_time
            
            self.logger.debug(
                f"Category crawl completed for {category_url}: "
                f"{len(discovered_urls)} URLs from {category_info['pages_crawled']} pages",
                tag="CATEGORY_CRAWLER"
            )
            
            return discovered_urls, category_info
            
        except Exception as e:
            category_info["error"] = str(e)
            category_info["processing_time"] = time.time() - start_time
            
            self.logger.error(
                f"Error crawling category {category_url}: {str(e)}",
                tag="CATEGORY_CRAWLER"
            )
            
            return [], category_info
    
    async def _crawl_category_page(
        self,
        page_url: str,
        category_source: str,
        depth: int,
        config: CategoryConfig
    ) -> Tuple[List[CategoryURL], Dict[str, Any]]:
        """
        Crawl a single category page and extract article URLs.
        
        Args:
            page_url: URL of the page to crawl
            category_source: Original category URL
            depth: Current crawl depth
            config: Crawling configuration
            
        Returns:
            Tuple of (discovered URLs, page info)
        """
        page_info = {"success": False, "urls_found": 0}
        
        try:
            # Fetch page content
            response = await self.client.get(page_url)
            response.raise_for_status()
            
            content = response.text
            
            # Extract article URLs from page content
            urls = await self._extract_article_urls(content, page_url, config)
            
            # Create CategoryURL objects
            category_urls = []
            for url in urls:
                category_url = CategoryURL(
                    url=url,
                    category_source=category_source,
                    discovered_depth=depth,
                    page_number=self._extract_page_number(page_url)
                )
                category_urls.append(category_url)
            
            page_info["success"] = True
            page_info["urls_found"] = len(category_urls)
            
            return category_urls, page_info
            
        except Exception as e:
            self.logger.debug(
                f"Error crawling page {page_url}: {str(e)}",
                tag="CATEGORY_CRAWLER"
            )
            page_info["error"] = str(e)
            return [], page_info
    
    async def _extract_article_urls(
        self,
        content: str,
        base_url: str,
        config: CategoryConfig
    ) -> List[str]:
        """Extract article URLs from page content."""
        urls = []
        
        # Extract all links
        link_pattern = r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>'
        matches = re.findall(link_pattern, content, re.IGNORECASE)
        
        for url in matches:
            # Make URL absolute
            if url.startswith('/'):
                parsed_base = urlparse(base_url)
                url = f"{parsed_base.scheme}://{parsed_base.netloc}{url}"
            elif not url.startswith('http'):
                url = urljoin(base_url, url)
            
            # Apply filters
            if self._should_include_url(url, config):
                urls.append(url)
        
        return urls
    
    def _should_include_url(self, url: str, config: CategoryConfig) -> bool:
        """Determine if URL should be included based on filters."""
        url_lower = url.lower()
        
        # Exclude patterns
        for pattern in config.exclude_patterns:
            pattern_regex = pattern.replace('*', '.*')
            if re.search(pattern_regex, url_lower):
                return False
        
        # Include Vietnamese news patterns
        if config.vietnamese_optimization:
            for pattern in self.vietnamese_category_patterns:
                if pattern in url_lower:
                    return True
            
            # Check for Vietnamese date patterns
            if re.search(r'/\d{4}/\d{2}/', url) or re.search(r'/\d{6,8}/', url):
                return True
        
        # Check for article-like URLs
        article_indicators = [
            '/chi-tiet/', '/bai-viet/', '/tin/', '/news/', '/article/',
            '.html', '.htm', '/p/', '/post/'
        ]
        
        return any(indicator in url_lower for indicator in article_indicators)
    
    async def _discover_pagination(self, page_url: str, config: CategoryConfig) -> List[str]:
        """Discover pagination URLs from the current page."""
        try:
            response = await self.client.get(page_url)
            content = response.text
            
            pagination_urls = []
            
            # Extract pagination links
            link_pattern = r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>([^<]+)</a>'
            matches = re.findall(link_pattern, content, re.IGNORECASE)
            
            for url, text in matches:
                text_lower = text.lower().strip()
                
                # Check for Vietnamese pagination text
                if any(pattern in text_lower for pattern in ['trang', 'page', 'tiếp', 'next', 'sau']):
                    # Make URL absolute
                    if url.startswith('/'):
                        parsed_base = urlparse(page_url)
                        url = f"{parsed_base.scheme}://{parsed_base.netloc}{url}"
                    elif not url.startswith('http'):
                        url = urljoin(page_url, url)
                    
                    pagination_urls.append(url)
                
                # Check for numeric pagination
                if re.match(r'^\d+$', text_lower):
                    if url.startswith('/'):
                        parsed_base = urlparse(page_url)
                        url = f"{parsed_base.scheme}://{parsed_base.netloc}{url}"
                    elif not url.startswith('http'):
                        url = urljoin(page_url, url)
                    
                    pagination_urls.append(url)
            
            return pagination_urls[:10]  # Limit pagination URLs
            
        except Exception as e:
            self.logger.debug(f"Error discovering pagination for {page_url}: {str(e)}", tag="CATEGORY_CRAWLER")
            return []
    
    async def _discover_subcategories(self, page_url: str, config: CategoryConfig) -> List[str]:
        """Discover subcategory URLs from the current page."""
        try:
            response = await self.client.get(page_url)
            content = response.text
            
            subcategory_urls = []
            
            # Look for navigation menus and category lists
            nav_pattern = r'<(?:nav|ul|div)[^>]*(?:class|id)=["\'][^"\']*(?:menu|nav|category|section)[^"\']*["\'][^>]*>(.*?)</(?:nav|ul|div)>'
            nav_matches = re.findall(nav_pattern, content, re.IGNORECASE | re.DOTALL)
            
            for nav_content in nav_matches:
                # Extract links from navigation content
                link_pattern = r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>([^<]+)</a>'
                link_matches = re.findall(link_pattern, nav_content, re.IGNORECASE)
                
                for url, text in link_matches:
                    text_lower = text.lower().strip()
                    
                    # Check if link text contains Vietnamese category keywords
                    if any(keyword in text_lower for keyword in config.content_keywords):
                        # Make URL absolute
                        if url.startswith('/'):
                            parsed_base = urlparse(page_url)
                            url = f"{parsed_base.scheme}://{parsed_base.netloc}{url}"
                        elif not url.startswith('http'):
                            url = urljoin(page_url, url)
                        
                        subcategory_urls.append(url)
            
            return subcategory_urls[:5]  # Limit subcategories
            
        except Exception as e:
            self.logger.debug(f"Error discovering subcategories for {page_url}: {str(e)}", tag="CATEGORY_CRAWLER")
            return []
    
    def _extract_page_number(self, url: str) -> Optional[int]:
        """Extract page number from URL if available."""
        # Try to extract page number from URL
        for pattern in [r'page=(\d+)', r'p=(\d+)', r'trang=(\d+)', r'/(\d+)/?$']:
            match = re.search(pattern, url, re.IGNORECASE)
            if match:
                try:
                    return int(match.group(1))
                except ValueError:
                    continue
        
        return None
    
    async def _apply_vietnamese_scoring(
        self,
        urls: List[CategoryURL],
        config: CategoryConfig
    ) -> List[CategoryURL]:
        """Apply Vietnamese content scoring to discovered URLs."""
        
        for url_obj in urls:
            score = 0.0
            url_lower = url_obj.url.lower()
            
            # Vietnamese URL pattern scoring
            for pattern in self.vietnamese_category_patterns:
                if pattern in url_lower:
                    score += 0.3
                    break
            
            # Vietnamese domain indicators
            if any(indicator in url_lower for indicator in ['.vn/', 'vietnam', 'viet']):
                score += 0.2
            
            # Date patterns (Vietnamese news often includes dates)
            if re.search(r'/\d{4}/\d{2}/', url_lower) or re.search(r'/\d{6,8}/', url_lower):
                score += 0.2
            
            # Article URL patterns
            if any(pattern in url_lower for pattern in ['/tin-', '/bai-', '/chi-tiet', '.html']):
                score += 0.3
            
            url_obj.vietnamese_score = min(score, 1.0)
            
            # Calculate relevance score based on keywords
            keyword_matches = sum(1 for keyword in config.content_keywords if keyword in url_lower)
            url_obj.relevance_score = keyword_matches / len(config.content_keywords) if config.content_keywords else 0
        
        return urls
    
    async def _deduplicate_urls(self, urls: List[CategoryURL]) -> List[CategoryURL]:
        """Remove duplicate URLs while preserving best scores."""
        
        seen_urls = {}
        
        for url_obj in urls:
            url = url_obj.url
            
            if url not in seen_urls:
                seen_urls[url] = url_obj
            else:
                # Keep the one with better scores
                existing = seen_urls[url]
                combined_score = url_obj.vietnamese_score + url_obj.relevance_score
                existing_combined = existing.vietnamese_score + existing.relevance_score
                
                if combined_score > existing_combined:
                    seen_urls[url] = url_obj
        
        return list(seen_urls.values())
    
    def _calculate_performance_metrics(
        self,
        categories_processed: List[Dict[str, Any]],
        urls: List[CategoryURL],
        execution_time: float
    ) -> Dict[str, Any]:
        """Calculate performance metrics for the crawl."""
        
        successful_categories = [cat for cat in categories_processed if cat.get("success", False)]
        
        return {
            "successful_categories": len(successful_categories),
            "failed_categories": len(categories_processed) - len(successful_categories),
            "total_pages_per_category": sum(cat.get("pages_crawled", 0) for cat in successful_categories) / len(successful_categories) if successful_categories else 0,
            "urls_per_category": len(urls) / len(successful_categories) if successful_categories else 0,
            "urls_per_second": len(urls) / execution_time if execution_time > 0 else 0,
            "vietnamese_url_percentage": len([u for u in urls if u.vietnamese_score > 0.3]) / len(urls) if urls else 0,
            "average_vietnamese_score": sum(u.vietnamese_score for u in urls) / len(urls) if urls else 0,
            "pagination_success_rate": sum(cat.get("pagination_pages", 0) for cat in successful_categories) / len(successful_categories) if successful_categories else 0
        }
    
    def _update_performance_stats(self, result: CategoryCrawlResult):
        """Update internal performance statistics."""
        self.performance_stats["total_categories_processed"] += len(result.categories_processed)
        self.performance_stats["total_urls_discovered"] += len(result.discovered_urls)
        self.performance_stats["total_pages_crawled"] += result.total_pages_crawled
        
        # Update averages
        current_avg = self.performance_stats["average_processing_time"]
        if current_avg == 0:
            self.performance_stats["average_processing_time"] = result.execution_time
        else:
            self.performance_stats["average_processing_time"] = (current_avg + result.execution_time) / 2
        
        # Update success rates
        if result.categories_processed:
            successful_categories = len([c for c in result.categories_processed if c.get("success", False)])
            success_rate = successful_categories / len(result.categories_processed)
            
            current_pagination_rate = self.performance_stats["pagination_success_rate"]
            if current_pagination_rate == 0:
                self.performance_stats["pagination_success_rate"] = result.pagination_discovered / max(result.total_pages_crawled, 1)
            else:
                new_rate = result.pagination_discovered / max(result.total_pages_crawled, 1)
                self.performance_stats["pagination_success_rate"] = (current_pagination_rate + new_rate) / 2
        
        # Vietnamese content rate
        if result.discovered_urls:
            vietnamese_urls = len([u for u in result.discovered_urls if u.vietnamese_score > 0.3])
            vietnamese_rate = vietnamese_urls / len(result.discovered_urls)
            
            current_vn_rate = self.performance_stats["vietnamese_content_rate"]
            if current_vn_rate == 0:
                self.performance_stats["vietnamese_content_rate"] = vietnamese_rate
            else:
                self.performance_stats["vietnamese_content_rate"] = (current_vn_rate + vietnamese_rate) / 2
        
        self.performance_stats["last_crawl_time"] = datetime.utcnow().isoformat()
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get current performance statistics."""
        return self.performance_stats.copy()
    
    async def close(self):
        """Clean up resources."""
        await self.client.aclose()
        self.logger.info("Category crawler closed", tag="CATEGORY_CRAWLER")