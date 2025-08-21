"""
Deep Crawling Fallback - Fallback strategies for difficult domains

This module implements comprehensive fallback crawling strategies for Vietnamese news domains
that don't have standard discovery methods (RSS, sitemaps, categories).

Features:
- BFS/BestFirst crawling strategies với configurable depth
- Pattern-based URL discovery cho difficult domains  
- Heuristic analysis cho limited discoverability domains
- Adaptive crawl depth adjustment based on results
- Performance tracking và intelligent stopping conditions
"""

import asyncio
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse, urljoin
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
from crawl4ai.deep_crawling.bff_strategy import BestFirstCrawlStrategy
from crawl4ai.deep_crawling.filters import FilterChain, URLPatternFilter, ContentRelevanceFilter, ContentTypeFilter
from crawl4ai.deep_crawling.scorers import KeywordRelevanceScorer, PathDepthScorer, CompositeScorer
from crawl4ai.async_logger import AsyncLogger

@dataclass
class FallbackConfig:
    """Configuration for fallback crawling strategies."""
    domain: str
    base_url: str
    strategy: str = "adaptive"  # "bfs", "best_first", "adaptive"
    max_depth: int = 4
    max_urls: int = 1000
    max_concurrent: int = 5
    vietnamese_optimization: bool = True
    content_keywords: List[str] = None
    url_patterns: List[str] = None
    exclude_patterns: List[str] = None
    adaptive_threshold: int = 50  # Switch strategies if not finding enough URLs
    timeout_minutes: int = 10
    
    def __post_init__(self):
        if self.content_keywords is None:
            self.content_keywords = [
                "tin tức", "báo chí", "thời sự", "kinh tế", "xã hội", 
                "thể thao", "pháp luật", "giáo dục", "sức khỏe", "công nghệ",
                "chính trị", "quốc tế", "văn hóa", "giải trí", "du lịch"
            ]
        if self.url_patterns is None:
            self.url_patterns = [
                "*/tin-tuc/*", "*/bao-chi/*", "*/thoi-su/*", "*/news/*",
                "*/kinh-te/*", "*/xa-hoi/*", "*/the-thao/*", "*/phap-luat/*",
                "*/giao-duc/*", "*/suc-khoe/*", "*/cong-nghe/*", "*/chinh-tri/*"
            ]
        if self.exclude_patterns is None:
            self.exclude_patterns = [
                "*/search/*", "*/tag/*", "*/author/*", "*/archive/*",
                "*/admin/*", "*/login/*", "*/register/*", "*/wp-admin/*",
                "*/api/*", "*/ajax/*", "*/rss/*", "*/feed/*", "*.css",
                "*.js", "*.jpg", "*.png", "*.gif", "*.pdf", "*.zip"
            ]

@dataclass
class FallbackURL:
    """Represents a URL discovered through fallback crawling."""
    url: str
    discovery_strategy: str
    depth: int
    score: float = 0.0
    vietnamese_score: float = 0.0
    parent_url: Optional[str] = None
    discovered_at: datetime = None
    heuristic_indicators: List[str] = None
    
    def __post_init__(self):
        if self.discovered_at is None:
            self.discovered_at = datetime.utcnow()
        if self.heuristic_indicators is None:
            self.heuristic_indicators = []

@dataclass
class FallbackCrawlResult:
    """Result from fallback crawling operation."""
    domain: str
    strategy_used: str
    success: bool
    discovered_urls: List[FallbackURL]
    max_depth_reached: int
    total_pages_crawled: int
    strategies_attempted: List[str]
    execution_time: float
    stop_reason: str = "completed"  # completed, timeout, max_urls, no_more_urls
    error: Optional[str] = None
    performance_metrics: Dict[str, Any] = None
    heuristic_analysis: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.performance_metrics is None:
            self.performance_metrics = {}
        if self.heuristic_analysis is None:
            self.heuristic_analysis = {}

class DeepCrawlingFallback:
    """
    Intelligent fallback crawler for difficult Vietnamese news domains.
    
    Implements multiple crawling strategies with adaptive switching and
    heuristic analysis for domains with limited discoverability.
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
        
        # HTTP client for basic checks
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers={"User-Agent": self.user_agent},
            follow_redirects=True
        )
        
        # Vietnamese URL patterns for heuristic analysis
        self.vietnamese_url_patterns = [
            # News patterns
            r'/tin-tuc/', r'/thoi-su/', r'/bao-chi/', r'/news/',
            # Category patterns  
            r'/kinh-te/', r'/xa-hoi/', r'/the-thao/', r'/phap-luat/',
            r'/giao-duc/', r'/suc-khoe/', r'/cong-nghe/', r'/chinh-tri/',
            r'/quoc-te/', r'/van-hoa/', r'/giai-tri/', r'/du-lich/',
            # Date patterns
            r'/\d{4}/\d{2}/', r'/\d{6}/', r'/\d{8}/',
            # Article patterns
            r'/bai-viet/', r'/chi-tiet/', r'/tin/', r'/post/', r'/p\d+/',
            # Vietnamese specific
            r'-vn\.', r'vietnam', r'saigon', r'hanoi'
        ]
        
        # Content indicators for Vietnamese news
        self.content_indicators = [
            # Vietnamese text indicators
            "tin tức", "báo chí", "thời sự", "hôm nay", "mới nhất",
            "theo", "cho biết", "thông tin", "phóng viên", "nguồn tin",
            # Date/time indicators
            "ngày", "tháng", "năm", "giờ", "phút",
            "sáng", "chiều", "tối", "đêm", "hôm qua", "ngày mai",
            # News structure indicators
            "bài viết", "tin liên quan", "cùng chuyên mục", "xem thêm"
        ]
        
        # Performance tracking
        self.performance_stats = {
            "total_domains_processed": 0,
            "successful_crawls": 0,
            "failed_crawls": 0,
            "total_urls_discovered": 0,
            "strategy_success_rates": {
                "bfs": {"attempts": 0, "successes": 0},
                "best_first": {"attempts": 0, "successes": 0},
                "adaptive": {"attempts": 0, "successes": 0}
            },
            "average_depth_reached": 0.0,
            "average_execution_time": 0.0,
            "last_crawl_time": None
        }
    
    async def crawl_fallback(self, config: FallbackConfig) -> FallbackCrawlResult:
        """
        Execute fallback crawling with adaptive strategy selection.
        
        Args:
            config: Fallback crawling configuration
            
        Returns:
            FallbackCrawlResult with discovered URLs and analysis
        """
        start_time = time.time()
        timeout_time = start_time + (config.timeout_minutes * 60)
        
        try:
            self.logger.info(
                f"Starting fallback crawl for {config.domain} using {config.strategy} strategy",
                tag="FALLBACK_CRAWLER"
            )
            
            # Perform initial domain analysis
            heuristic_analysis = await self._analyze_domain_heuristics(config)
            
            # Adjust strategy based on heuristic analysis
            if config.strategy == "adaptive":
                recommended_strategy = self._recommend_strategy(heuristic_analysis)
                self.logger.info(f"Adaptive strategy recommends: {recommended_strategy}", tag="FALLBACK_CRAWLER")
            else:
                recommended_strategy = config.strategy
            
            # Execute crawling strategies
            strategies_attempted = []
            all_discovered_urls = []
            max_depth_reached = 0
            pages_crawled = 0
            stop_reason = "completed"
            
            # Try primary strategy
            result = await self._execute_strategy(
                recommended_strategy, config, timeout_time, heuristic_analysis
            )
            
            strategies_attempted.append(recommended_strategy)
            all_discovered_urls.extend(result["urls"])
            max_depth_reached = max(max_depth_reached, result["max_depth"])
            pages_crawled += result["pages_crawled"]
            
            # Check if we need to try additional strategies
            if (len(all_discovered_urls) < config.adaptive_threshold and 
                time.time() < timeout_time and
                config.strategy == "adaptive"):
                
                # Try alternative strategies
                alternative_strategies = ["bfs", "best_first"]
                if recommended_strategy in alternative_strategies:
                    alternative_strategies.remove(recommended_strategy)
                
                for alt_strategy in alternative_strategies:
                    if time.time() >= timeout_time:
                        stop_reason = "timeout"
                        break
                    
                    if len(all_discovered_urls) >= config.max_urls:
                        stop_reason = "max_urls"
                        break
                    
                    self.logger.info(f"Trying alternative strategy: {alt_strategy}", tag="FALLBACK_CRAWLER")
                    
                    alt_result = await self._execute_strategy(
                        alt_strategy, config, timeout_time, heuristic_analysis
                    )
                    
                    strategies_attempted.append(alt_strategy)
                    
                    # Merge results (avoiding duplicates)
                    existing_urls = {url.url for url in all_discovered_urls}
                    for url in alt_result["urls"]:
                        if url.url not in existing_urls:
                            all_discovered_urls.append(url)
                            existing_urls.add(url.url)
                    
                    max_depth_reached = max(max_depth_reached, alt_result["max_depth"])
                    pages_crawled += alt_result["pages_crawled"]
            
            # Check stop reasons
            if time.time() >= timeout_time:
                stop_reason = "timeout"
            elif len(all_discovered_urls) >= config.max_urls:
                stop_reason = "max_urls"
            elif len(all_discovered_urls) == 0:
                stop_reason = "no_urls_found"
            
            # Apply final filtering and scoring
            if config.vietnamese_optimization:
                all_discovered_urls = await self._apply_comprehensive_scoring(all_discovered_urls, config)
            
            # Sort by combined scores
            all_discovered_urls.sort(key=lambda x: (x.vietnamese_score, x.score), reverse=True)
            
            # Limit to max_urls
            final_urls = all_discovered_urls[:config.max_urls]
            
            execution_time = time.time() - start_time
            
            result = FallbackCrawlResult(
                domain=config.domain,
                strategy_used=recommended_strategy,
                success=True,
                discovered_urls=final_urls,
                max_depth_reached=max_depth_reached,
                total_pages_crawled=pages_crawled,
                strategies_attempted=strategies_attempted,
                execution_time=execution_time,
                stop_reason=stop_reason,
                performance_metrics=self._calculate_performance_metrics(final_urls, execution_time),
                heuristic_analysis=heuristic_analysis
            )
            
            self._update_performance_stats(result)
            
            self.logger.info(
                f"Fallback crawl completed for {config.domain}: "
                f"{len(final_urls)} URLs, depth {max_depth_reached}, "
                f"{len(strategies_attempted)} strategies in {execution_time:.2f}s",
                tag="FALLBACK_CRAWLER"
            )
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = str(e)
            
            self.logger.error(
                f"Fallback crawl failed for {config.domain}: {error_msg}",
                tag="FALLBACK_CRAWLER"
            )
            
            return FallbackCrawlResult(
                domain=config.domain,
                strategy_used=config.strategy,
                success=False,
                discovered_urls=[],
                max_depth_reached=0,
                total_pages_crawled=0,
                strategies_attempted=[],
                execution_time=execution_time,
                error=error_msg
            )
    
    async def _analyze_domain_heuristics(self, config: FallbackConfig) -> Dict[str, Any]:
        """
        Perform heuristic analysis of domain to guide strategy selection.
        
        Args:
            config: Fallback configuration
            
        Returns:
            Dictionary with heuristic analysis results
        """
        analysis = {
            "domain_structure": {},
            "vietnamese_indicators": {},
            "content_discovery": {},
            "navigation_complexity": "",
            "recommended_depth": config.max_depth
        }
        
        try:
            # Analyze homepage structure
            response = await self.client.get(config.base_url)
            if response.status_code == 200:
                content = response.text
                
                # Analyze domain structure
                analysis["domain_structure"] = await self._analyze_domain_structure(content, config.base_url)
                
                # Analyze Vietnamese content indicators
                analysis["vietnamese_indicators"] = await self._analyze_vietnamese_indicators(content)
                
                # Analyze content discovery potential
                analysis["content_discovery"] = await self._analyze_content_discovery(content, config.base_url)
                
                # Determine navigation complexity
                analysis["navigation_complexity"] = self._determine_navigation_complexity(content)
                
                # Recommend optimal depth based on structure
                analysis["recommended_depth"] = self._recommend_crawl_depth(analysis)
        
        except Exception as e:
            self.logger.warning(f"Heuristic analysis failed for {config.domain}: {str(e)}", tag="FALLBACK_CRAWLER")
            analysis["analysis_error"] = str(e)
        
        return analysis
    
    async def _analyze_domain_structure(self, content: str, base_url: str) -> Dict[str, Any]:
        """Analyze domain structure from homepage content."""
        structure = {
            "has_main_navigation": False,
            "navigation_links": 0,
            "has_breadcrumbs": False,
            "has_pagination": False,
            "category_links": 0,
            "article_links": 0,
            "internal_links": 0
        }
        
        # Check for main navigation
        nav_patterns = [r'<nav[^>]*>', r'<ul[^>]*(?:class|id)=["\'][^"\']*(?:menu|nav)[^"\']*["\']']
        structure["has_main_navigation"] = any(re.search(pattern, content, re.IGNORECASE) for pattern in nav_patterns)
        
        # Count navigation links
        nav_link_pattern = r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>([^<]+)</a>'
        links = re.findall(nav_link_pattern, content, re.IGNORECASE)
        
        for url, text in links:
            if url.startswith('/') or base_url in url:
                structure["internal_links"] += 1
                
                # Check if it's a category link
                text_lower = text.lower()
                if any(keyword in text_lower for keyword in ["tin tức", "thể thao", "kinh tế", "xã hội", "chính trí"]):
                    structure["category_links"] += 1
                
                # Check if it's an article link
                if any(pattern in url.lower() for pattern in ["/tin-", "/bai-", "/chi-tiet", ".html"]):
                    structure["article_links"] += 1
        
        structure["navigation_links"] = len([l for l in links if l[0].startswith('/') or base_url in l[0]])
        
        # Check for breadcrumbs
        breadcrumb_patterns = [r'breadcrumb', r'navigation', r'you are here']
        structure["has_breadcrumbs"] = any(re.search(pattern, content, re.IGNORECASE) for pattern in breadcrumb_patterns)
        
        # Check for pagination
        pagination_patterns = [r'trang \d+', r'page \d+', r'next', r'previous', r'tiếp theo']
        structure["has_pagination"] = any(re.search(pattern, content, re.IGNORECASE) for pattern in pagination_patterns)
        
        return structure
    
    async def _analyze_vietnamese_indicators(self, content: str) -> Dict[str, Any]:
        """Analyze Vietnamese content indicators."""
        indicators = {
            "vietnamese_text_density": 0.0,
            "news_keywords_found": 0,
            "date_patterns_found": 0,
            "vietnamese_url_patterns": 0,
            "content_confidence": 0.0
        }
        
        content_lower = content.lower()
        
        # Count Vietnamese news keywords
        news_keywords = [
            "tin tức", "báo chí", "thời sự", "phóng viên", "bản tin",
            "cập nhật", "nóng hổi", "mới nhất", "nhanh nhất"
        ]
        indicators["news_keywords_found"] = sum(1 for keyword in news_keywords if keyword in content_lower)
        
        # Count date patterns
        date_patterns = [r'\d+/\d+/\d+', r'\d+ tháng \d+', r'hôm nay', r'hôm qua', r'ngày \d+']
        indicators["date_patterns_found"] = sum(1 for pattern in date_patterns if re.search(pattern, content_lower))
        
        # Count Vietnamese URL patterns in links
        url_pattern = r'href=["\']([^"\']+)["\']'
        urls = re.findall(url_pattern, content)
        for url in urls:
            if any(re.search(pattern, url.lower()) for pattern in self.vietnamese_url_patterns):
                indicators["vietnamese_url_patterns"] += 1
        
        # Calculate Vietnamese text density (rough estimate)
        vietnamese_chars = sum(1 for char in content if ord(char) > 127)  # Non-ASCII characters
        if len(content) > 0:
            indicators["vietnamese_text_density"] = vietnamese_chars / len(content)
        
        # Calculate overall confidence
        confidence_factors = [
            min(indicators["news_keywords_found"] / 5, 1.0) * 0.4,
            min(indicators["date_patterns_found"] / 3, 1.0) * 0.3,  
            min(indicators["vietnamese_url_patterns"] / 10, 1.0) * 0.2,
            min(indicators["vietnamese_text_density"] * 10, 1.0) * 0.1
        ]
        indicators["content_confidence"] = sum(confidence_factors)
        
        return indicators
    
    async def _analyze_content_discovery(self, content: str, base_url: str) -> Dict[str, Any]:
        """Analyze content discovery potential."""
        discovery = {
            "archive_links": 0,
            "category_depth": 0,
            "pagination_indicators": 0,
            "search_functionality": False,
            "rss_feeds": 0,
            "sitemap_hints": 0
        }
        
        content_lower = content.lower()
        
        # Check for archive links
        archive_patterns = ["archive", "lưu trữ", "các tin cũ", "tin cũ"]
        discovery["archive_links"] = sum(1 for pattern in archive_patterns if pattern in content_lower)
        
        # Estimate category depth by looking at nested category structures
        category_structure = re.findall(r'<ul[^>]*>.*?<li[^>]*>.*?<ul[^>]*>', content, re.DOTALL | re.IGNORECASE)
        discovery["category_depth"] = len(category_structure)
        
        # Count pagination indicators
        pagination_patterns = ["trang", "page", ">>", "next", "previous", "tiếp theo", "trước"]
        discovery["pagination_indicators"] = sum(1 for pattern in pagination_patterns if pattern in content_lower)
        
        # Check for search functionality
        search_indicators = ["<input[^>]*search", "<form[^>]*search", "tìm kiếm", "search"]
        discovery["search_functionality"] = any(re.search(pattern, content, re.IGNORECASE) for pattern in search_indicators)
        
        # Look for RSS feed links
        rss_pattern = r'<link[^>]*(?:application/rss|application/atom)[^>]*>'
        discovery["rss_feeds"] = len(re.findall(rss_pattern, content, re.IGNORECASE))
        
        # Look for sitemap hints
        sitemap_patterns = ["sitemap", "sơ đồ trang web"]
        discovery["sitemap_hints"] = sum(1 for pattern in sitemap_patterns if pattern in content_lower)
        
        return discovery
    
    def _determine_navigation_complexity(self, content: str) -> str:
        """Determine navigation complexity level."""
        # Simple heuristic based on DOM structure complexity
        tag_count = len(re.findall(r'<[^>]+>', content))
        link_count = len(re.findall(r'<a[^>]+href', content, re.IGNORECASE))
        
        if tag_count > 5000 and link_count > 200:
            return "high"
        elif tag_count > 2000 and link_count > 50:
            return "medium"
        else:
            return "low"
    
    def _recommend_crawl_depth(self, analysis: Dict[str, Any]) -> int:
        """Recommend optimal crawl depth based on heuristic analysis."""
        base_depth = 3
        
        # Increase depth if we have good navigation structure
        structure = analysis.get("domain_structure", {})
        if structure.get("has_main_navigation") and structure.get("category_links", 0) > 5:
            base_depth += 1
        
        # Increase depth if content discovery looks promising
        discovery = analysis.get("content_discovery", {})
        if discovery.get("category_depth", 0) > 2:
            base_depth += 1
        
        # Decrease depth if navigation is too complex
        if analysis.get("navigation_complexity") == "high":
            base_depth = max(base_depth - 1, 2)
        
        # Increase depth if Vietnamese content confidence is high
        vietnamese = analysis.get("vietnamese_indicators", {})
        if vietnamese.get("content_confidence", 0) > 0.7:
            base_depth += 1
        
        return min(base_depth, 6)  # Cap at reasonable maximum
    
    def _recommend_strategy(self, analysis: Dict[str, Any]) -> str:
        """Recommend crawling strategy based on heuristic analysis."""
        
        # Get key metrics
        structure = analysis.get("domain_structure", {})
        discovery = analysis.get("content_discovery", {})
        complexity = analysis.get("navigation_complexity", "medium")
        vietnamese_confidence = analysis.get("vietnamese_indicators", {}).get("content_confidence", 0)
        
        # High navigation complexity or many category links -> BFS
        if complexity == "high" or structure.get("category_links", 0) > 10:
            return "bfs"
        
        # Good Vietnamese content confidence and structured navigation -> Best First
        if vietnamese_confidence > 0.6 and structure.get("has_main_navigation"):
            return "best_first"
        
        # Default to BFS for most Vietnamese news sites
        return "bfs"
    
    async def _execute_strategy(
        self,
        strategy: str,
        config: FallbackConfig,
        timeout_time: float,
        heuristic_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a specific crawling strategy."""
        
        try:
            # Create filter chain
            filter_chain = self._create_filter_chain(config)
            
            # Create scorer if using best-first strategy
            scorer = None
            if strategy == "best_first":
                scorer = self._create_vietnamese_scorer(config)
            
            # Adjust parameters based on heuristic analysis
            max_depth = heuristic_analysis.get("recommended_depth", config.max_depth)
            
            discovered_urls = []
            
            if strategy == "bfs":
                bfs_strategy = BFSDeepCrawlStrategy(
                    max_depth=max_depth,
                    filter_chain=filter_chain,
                    url_scorer=scorer,
                    max_pages=min(config.max_urls, 500),  # Reasonable limit
                    include_external=False
                )
                
                # Note: This is a simplified implementation
                # In actual implementation, you would use the strategy with AsyncWebCrawler
                urls = await self._simulate_crawl_strategy("bfs", config, max_depth, timeout_time)
                
            elif strategy == "best_first":
                bf_strategy = BestFirstCrawlStrategy(
                    max_depth=max_depth,
                    filter_chain=filter_chain,
                    scorer=scorer,
                    max_pages=min(config.max_urls, 500),
                    include_external=False
                )
                
                # Note: This is a simplified implementation
                urls = await self._simulate_crawl_strategy("best_first", config, max_depth, timeout_time)
            
            else:
                # Default to BFS
                urls = await self._simulate_crawl_strategy("bfs", config, max_depth, timeout_time)
            
            return {
                "urls": urls,
                "max_depth": max_depth,
                "pages_crawled": len(urls)
            }
            
        except Exception as e:
            self.logger.error(f"Strategy execution failed for {strategy}: {str(e)}", tag="FALLBACK_CRAWLER")
            return {
                "urls": [],
                "max_depth": 0,
                "pages_crawled": 0,
                "error": str(e)
            }
    
    async def _simulate_crawl_strategy(
        self,
        strategy: str,
        config: FallbackConfig,
        max_depth: int,
        timeout_time: float
    ) -> List[FallbackURL]:
        """
        Simulate crawling strategy execution.
        
        Note: This is a simplified implementation for demonstration.
        In actual implementation, you would integrate with AsyncWebCrawler.
        """
        discovered_urls = []
        visited_urls = set()
        urls_to_visit = [(config.base_url, 0, None)]  # (url, depth, parent)
        
        while urls_to_visit and time.time() < timeout_time and len(discovered_urls) < config.max_urls:
            current_url, depth, parent_url = urls_to_visit.pop(0)
            
            if current_url in visited_urls or depth > max_depth:
                continue
            
            visited_urls.add(current_url)
            
            try:
                # Fetch page content
                response = await self.client.get(current_url)
                if response.status_code != 200:
                    continue
                
                content = response.text
                
                # Extract links from page
                new_urls = await self._extract_and_filter_links(content, current_url, config)
                
                # Create FallbackURL objects
                for url in new_urls:
                    if url not in visited_urls:
                        fallback_url = FallbackURL(
                            url=url,
                            discovery_strategy=strategy,
                            depth=depth + 1,
                            parent_url=current_url
                        )
                        
                        # Apply heuristic scoring
                        fallback_url.score = self._calculate_url_score(url, config)
                        
                        discovered_urls.append(fallback_url)
                        
                        # Add to crawl queue if not too deep
                        if depth + 1 <= max_depth:
                            urls_to_visit.append((url, depth + 1, current_url))
                
                # Sort urls_to_visit by score if using best-first
                if strategy == "best_first":
                    urls_to_visit.sort(key=lambda x: self._calculate_url_score(x[0], config), reverse=True)
                
            except Exception as e:
                self.logger.debug(f"Error crawling {current_url}: {str(e)}", tag="FALLBACK_CRAWLER")
                continue
        
        return discovered_urls
    
    async def _extract_and_filter_links(self, content: str, base_url: str, config: FallbackConfig) -> List[str]:
        """Extract and filter links from page content."""
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
            if self._should_crawl_url(url, config):
                urls.append(url)
        
        return urls
    
    def _should_crawl_url(self, url: str, config: FallbackConfig) -> bool:
        """Determine if URL should be crawled based on filters."""
        url_lower = url.lower()
        
        # Must be from same domain
        if config.domain.lower() not in url_lower:
            return False
        
        # Check exclude patterns
        for pattern in config.exclude_patterns:
            pattern_regex = pattern.replace('*', '.*')
            if re.search(pattern_regex, url_lower):
                return False
        
        # Check include patterns
        for pattern in config.url_patterns:
            pattern_regex = pattern.replace('*', '.*')
            if re.search(pattern_regex, url_lower):
                return True
        
        # Check for Vietnamese news indicators
        if any(re.search(pattern, url_lower) for pattern in self.vietnamese_url_patterns):
            return True
        
        return False
    
    def _calculate_url_score(self, url: str, config: FallbackConfig) -> float:
        """Calculate relevance score for URL."""
        score = 0.0
        url_lower = url.lower()
        
        # Vietnamese URL patterns
        for pattern in self.vietnamese_url_patterns:
            if re.search(pattern, url_lower):
                score += 0.3
                break
        
        # Keyword matching
        for keyword in config.content_keywords:
            if keyword.lower() in url_lower:
                score += 0.2
        
        # Depth scoring (prefer shallower URLs)
        depth = url_lower.count('/') - 2  # Subtract protocol and domain
        if depth <= 3:
            score += 0.3
        elif depth <= 5:
            score += 0.1
        
        # Article-like URLs get higher scores
        article_indicators = ['/tin-', '/bai-', '/chi-tiet', '.html', '/news/', '/p/']
        if any(indicator in url_lower for indicator in article_indicators):
            score += 0.4
        
        return min(score, 1.0)
    
    def _create_filter_chain(self, config: FallbackConfig) -> FilterChain:
        """Create filter chain for crawling."""
        filters = []
        
        # URL pattern filter
        url_filter = URLPatternFilter(patterns=config.url_patterns)
        filters.append(url_filter)
        
        # Content relevance filter
        content_filter = ContentRelevanceFilter(
            query=" ".join(config.content_keywords),
            threshold=0.3
        )
        filters.append(content_filter)
        
        # Content type filter
        type_filter = ContentTypeFilter(allowed_types=["text/html"])
        filters.append(type_filter)
        
        return FilterChain(filters)
    
    def _create_vietnamese_scorer(self, config: FallbackConfig) -> CompositeScorer:
        """Create composite scorer optimized for Vietnamese content."""
        scorers = []
        
        # Keyword relevance scorer
        keyword_scorer = KeywordRelevanceScorer(
            keywords=config.content_keywords,
            weight=0.5
        )
        scorers.append(keyword_scorer)
        
        # Path depth scorer (prefer not too deep)
        depth_scorer = PathDepthScorer(
            optimal_depth=3,
            weight=0.3
        )
        scorers.append(depth_scorer)
        
        return CompositeScorer(scorers, normalize=True)
    
    async def _apply_comprehensive_scoring(
        self,
        urls: List[FallbackURL],
        config: FallbackConfig
    ) -> List[FallbackURL]:
        """Apply comprehensive Vietnamese content scoring."""
        
        for url_obj in urls:
            vietnamese_score = 0.0
            url_lower = url_obj.url.lower()
            
            # URL structure scoring
            for pattern in self.vietnamese_url_patterns:
                if re.search(pattern, url_lower):
                    vietnamese_score += 0.2
                    url_obj.heuristic_indicators.append(f"url_pattern:{pattern}")
            
            # Domain indicators
            if any(indicator in url_lower for indicator in ['.vn/', 'vietnam', 'viet']):
                vietnamese_score += 0.3
                url_obj.heuristic_indicators.append("domain_indicator")
            
            # Content keywords in URL
            keyword_matches = sum(1 for keyword in config.content_keywords if keyword.lower() in url_lower)
            if keyword_matches > 0:
                vietnamese_score += (keyword_matches / len(config.content_keywords)) * 0.3
                url_obj.heuristic_indicators.append(f"keyword_matches:{keyword_matches}")
            
            # Article structure indicators
            article_indicators = ['/tin-', '/bai-', '/chi-tiet', '.html', '/news/']
            for indicator in article_indicators:
                if indicator in url_lower:
                    vietnamese_score += 0.2
                    url_obj.heuristic_indicators.append(f"article_indicator:{indicator}")
                    break
            
            url_obj.vietnamese_score = min(vietnamese_score, 1.0)
        
        return urls
    
    def _calculate_performance_metrics(self, urls: List[FallbackURL], execution_time: float) -> Dict[str, Any]:
        """Calculate performance metrics for the crawl."""
        
        if not urls:
            return {
                "urls_per_second": 0,
                "average_score": 0,
                "average_vietnamese_score": 0,
                "depth_distribution": {},
                "strategy_distribution": {}
            }
        
        return {
            "urls_per_second": len(urls) / execution_time if execution_time > 0 else 0,
            "average_score": sum(url.score for url in urls) / len(urls),
            "average_vietnamese_score": sum(url.vietnamese_score for url in urls) / len(urls),
            "depth_distribution": {str(d): len([u for u in urls if u.depth == d]) for d in range(7)},
            "strategy_distribution": {
                strategy: len([u for u in urls if u.discovery_strategy == strategy])
                for strategy in set(url.discovery_strategy for url in urls)
            },
            "high_quality_urls": len([u for u in urls if u.vietnamese_score > 0.7]),
            "heuristic_indicators": [indicator for url in urls for indicator in url.heuristic_indicators]
        }
    
    def _update_performance_stats(self, result: FallbackCrawlResult):
        """Update internal performance statistics."""
        self.performance_stats["total_domains_processed"] += 1
        
        if result.success:
            self.performance_stats["successful_crawls"] += 1
            self.performance_stats["total_urls_discovered"] += len(result.discovered_urls)
            
            # Update strategy success rates
            for strategy in result.strategies_attempted:
                self.performance_stats["strategy_success_rates"][strategy]["attempts"] += 1
                if result.success:
                    self.performance_stats["strategy_success_rates"][strategy]["successes"] += 1
        else:
            self.performance_stats["failed_crawls"] += 1
        
        # Update averages
        current_depth_avg = self.performance_stats["average_depth_reached"]
        current_time_avg = self.performance_stats["average_execution_time"]
        total_processed = self.performance_stats["total_domains_processed"]
        
        if total_processed > 1:
            self.performance_stats["average_depth_reached"] = (
                (current_depth_avg * (total_processed - 1) + result.max_depth_reached) / total_processed
            )
            self.performance_stats["average_execution_time"] = (
                (current_time_avg * (total_processed - 1) + result.execution_time) / total_processed
            )
        else:
            self.performance_stats["average_depth_reached"] = result.max_depth_reached
            self.performance_stats["average_execution_time"] = result.execution_time
        
        self.performance_stats["last_crawl_time"] = datetime.utcnow().isoformat()
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get current performance statistics."""
        stats = self.performance_stats.copy()
        
        # Calculate success rates
        for strategy in stats["strategy_success_rates"]:
            attempts = stats["strategy_success_rates"][strategy]["attempts"]
            successes = stats["strategy_success_rates"][strategy]["successes"]
            stats["strategy_success_rates"][strategy]["success_rate"] = (
                successes / attempts if attempts > 0 else 0
            )
        
        return stats
    
    async def close(self):
        """Clean up resources."""
        await self.client.aclose()
        self.logger.info("Deep crawling fallback closed", tag="FALLBACK_CRAWLER")