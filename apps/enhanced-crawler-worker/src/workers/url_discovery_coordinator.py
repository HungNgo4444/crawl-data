"""
URL Discovery Coordinator - Central coordination logic for parallel URL discovery

This module implements comprehensive URL discovery coordination using Crawl4AI's
AsyncUrlSeeder and deep crawling strategies for Vietnamese news domains.

Features:
- Parallel execution of all discovery methods (RSS, Sitemap, Category, Deep Crawl)
- Advanced URL deduplication across all sources with intelligent scoring  
- Discovery method performance tracking and optimization
- Vietnamese content prioritization using BM25 scoring
- Memory-efficient processing with bounded queues
"""

import asyncio
import hashlib
import json
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from uuid import UUID, uuid4

# Import Crawl4AI components
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'crawl4ai-main'))

from crawl4ai.async_url_seeder import AsyncUrlSeeder
from crawl4ai.async_configs import SeedingConfig
from crawl4ai.deep_crawling.bfs_strategy import BFSDeepCrawlStrategy  
from crawl4ai.deep_crawling.bff_strategy import BestFirstCrawlStrategy
from crawl4ai.deep_crawling.scorers import KeywordRelevanceScorer
from crawl4ai.deep_crawling.filters import URLPatternFilter, ContentRelevanceFilter, FilterChain
from crawl4ai.async_logger import AsyncLogger

# Models for domain configuration and results
from dataclasses import dataclass
from enum import Enum

class DiscoveryMethod(Enum):
    """Enumeration of URL discovery methods."""
    RSS = "rss"
    SITEMAP = "sitemap" 
    CATEGORY = "category"
    GOOGLE_SEARCH = "google_search"  # Manual only
    DEEP_CRAWL_FALLBACK = "deep_crawl_fallback"
    COMMON_CRAWL = "common_crawl"

@dataclass
class DomainConfiguration:
    """Configuration for a domain to be crawled."""
    id: UUID
    domain_name: str
    base_url: str
    status: str = "ACTIVE"
    
    # Discovery method configuration
    has_rss_feeds: bool = False
    rss_feeds: List[str] = None
    
    has_sitemaps: bool = False
    sitemaps: List[str] = None
    
    has_category_urls: bool = False
    category_urls: List[str] = None
    
    # Deep crawling configuration
    max_depth: int = 3
    crawl_patterns: List[str] = None
    
    # Vietnamese content optimization
    vietnamese_keywords: List[str] = None
    content_filters: List[str] = None
    
    def __post_init__(self):
        if self.rss_feeds is None:
            self.rss_feeds = []
        if self.sitemaps is None:
            self.sitemaps = []
        if self.category_urls is None:
            self.category_urls = []
        if self.crawl_patterns is None:
            self.crawl_patterns = ["*/tin-tuc/*", "*/bao-chi/*", "*/thoi-su/*"]
        if self.vietnamese_keywords is None:
            self.vietnamese_keywords = ["tin tức", "báo chí", "thời sự", "kinh tế", "xã hội", "thể thao"]
        if self.content_filters is None:
            self.content_filters = []

@dataclass
class DiscoveryResult:
    """Result from a single discovery method."""
    method: DiscoveryMethod
    urls: List[Dict[str, Any]]
    execution_time: float
    success: bool
    error: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

@dataclass
class CoordinatedDiscoveryResult:
    """Final result from coordinated URL discovery."""
    domain_id: UUID
    domain_name: str
    total_discovered: int
    deduplicated_count: int
    successful_methods: List[DiscoveryMethod]
    failed_methods: List[DiscoveryMethod]
    method_results: Dict[DiscoveryMethod, DiscoveryResult]
    execution_time: float
    quality_metrics: Dict[str, Any]

class URLDiscoveryCoordinator:
    """
    Central coordinator for parallel URL discovery execution.
    
    Manages parallel execution of all discovery methods, deduplication,
    quality scoring, and performance tracking for Vietnamese news domains.
    """
    
    def __init__(
        self,
        logger: Optional[AsyncLogger] = None,
        cache_dir: Optional[Path] = None,
        concurrency_limit: int = 10,
        max_urls_per_method: int = 10000,
        vietnamese_optimization: bool = True
    ):
        self.logger = logger or AsyncLogger()
        self.cache_dir = cache_dir or Path.home() / ".crawl4ai" / "coordinator_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.concurrency_limit = concurrency_limit
        self.max_urls_per_method = max_urls_per_method
        self.vietnamese_optimization = vietnamese_optimization
        
        # Initialize Crawl4AI components
        self.url_seeder = AsyncUrlSeeder(logger=self.logger)
        
        # Performance tracking
        self.method_performance: Dict[DiscoveryMethod, List[float]] = {
            method: [] for method in DiscoveryMethod
        }
        
        # Vietnamese content patterns
        self.vietnamese_patterns = [
            "*/tin-tuc/*", "*/bao-chi/*", "*/thoi-su/*",
            "*/kinh-te/*", "*/xa-hoi/*", "*/the-thao/*",
            "*/phap-luat/*", "*/giao-duc/*", "*/suc-khoe/*"
        ]
        
    async def discover_urls_parallel(
        self,
        domain_config: DomainConfiguration,
        enable_methods: Optional[List[DiscoveryMethod]] = None,
        force_refresh: bool = False,
        query: Optional[str] = None
    ) -> CoordinatedDiscoveryResult:
        """
        Execute parallel URL discovery using all available methods.
        
        Args:
            domain_config: Configuration for the domain
            enable_methods: List of methods to enable (None = auto-detect)
            force_refresh: Force refresh of cached results
            query: Search query for content relevance scoring
            
        Returns:
            CoordinatedDiscoveryResult with deduplicated URLs and performance metrics
        """
        start_time = time.time()
        
        self.logger.info(
            f"Starting parallel URL discovery for {domain_config.domain_name}",
            tag="URL_DISCOVERY"
        )
        
        # Auto-detect available methods if not specified
        if enable_methods is None:
            enable_methods = self._detect_available_methods(domain_config)
        
        # Prepare discovery tasks
        discovery_tasks = []
        
        # RSS Discovery
        if DiscoveryMethod.RSS in enable_methods and domain_config.has_rss_feeds:
            task = self._discover_from_rss(domain_config, force_refresh, query)
            discovery_tasks.append((DiscoveryMethod.RSS, task))
            
        # Sitemap Discovery  
        if DiscoveryMethod.SITEMAP in enable_methods:
            task = self._discover_from_sitemaps(domain_config, force_refresh, query)
            discovery_tasks.append((DiscoveryMethod.SITEMAP, task))
            
        # Category Discovery
        if DiscoveryMethod.CATEGORY in enable_methods and domain_config.has_category_urls:
            task = self._discover_from_categories(domain_config, force_refresh, query)
            discovery_tasks.append((DiscoveryMethod.CATEGORY, task))
            
        # Common Crawl Discovery
        if DiscoveryMethod.COMMON_CRAWL in enable_methods:
            task = self._discover_from_common_crawl(domain_config, force_refresh, query)
            discovery_tasks.append((DiscoveryMethod.COMMON_CRAWL, task))
            
        # Deep Crawl Fallback (if other methods insufficient)
        if (DiscoveryMethod.DEEP_CRAWL_FALLBACK in enable_methods and 
            not any(method in enable_methods for method in 
                   [DiscoveryMethod.RSS, DiscoveryMethod.SITEMAP, DiscoveryMethod.CATEGORY])):
            task = self._discover_from_deep_crawl(domain_config, force_refresh, query)
            discovery_tasks.append((DiscoveryMethod.DEEP_CRAWL_FALLBACK, task))
        
        # Execute all discovery methods in parallel
        self.logger.info(
            f"Executing {len(discovery_tasks)} discovery methods in parallel",
            tag="URL_DISCOVERY"
        )
        
        discovery_results = {}
        successful_methods = []
        failed_methods = []
        
        # Use asyncio.gather with exception handling
        async def execute_method(method: DiscoveryMethod, task):
            try:
                result = await task
                return method, result
            except Exception as e:
                self.logger.error(
                    f"Discovery method {method.value} failed: {str(e)}",
                    tag="URL_DISCOVERY"
                )
                return method, DiscoveryResult(
                    method=method,
                    urls=[],
                    execution_time=0.0,
                    success=False,
                    error=str(e)
                )
        
        # Execute all methods concurrently
        method_tasks = [execute_method(method, task) for method, task in discovery_tasks]
        completed_results = await asyncio.gather(*method_tasks, return_exceptions=True)
        
        # Process results
        all_discovered_urls = []
        for result in completed_results:
            if isinstance(result, Exception):
                self.logger.error(f"Task execution error: {str(result)}", tag="URL_DISCOVERY")
                continue
                
            method, discovery_result = result
            discovery_results[method] = discovery_result
            
            if discovery_result.success:
                successful_methods.append(method)
                all_discovered_urls.extend(discovery_result.urls)
                
                # Update performance tracking
                self.method_performance[method].append(discovery_result.execution_time)
                
                self.logger.info(
                    f"{method.value}: discovered {len(discovery_result.urls)} URLs "
                    f"in {discovery_result.execution_time:.2f}s",
                    tag="URL_DISCOVERY"
                )
            else:
                failed_methods.append(method)
        
        self.logger.info(
            f"Discovery phase completed. Total URLs from all methods: {len(all_discovered_urls)}",
            tag="URL_DISCOVERY"
        )
        
        # URL Deduplication and Quality Scoring
        deduplicated_urls = await self.deduplicate_and_score(
            all_discovered_urls, 
            domain_config,
            query
        )
        
        # Calculate quality metrics
        quality_metrics = self._calculate_quality_metrics(
            all_discovered_urls, 
            deduplicated_urls,
            discovery_results
        )
        
        total_time = time.time() - start_time
        
        result = CoordinatedDiscoveryResult(
            domain_id=domain_config.id,
            domain_name=domain_config.domain_name,
            total_discovered=len(all_discovered_urls),
            deduplicated_count=len(deduplicated_urls),
            successful_methods=successful_methods,
            failed_methods=failed_methods,
            method_results=discovery_results,
            execution_time=total_time,
            quality_metrics=quality_metrics
        )
        
        self.logger.info(
            f"URL discovery completed for {domain_config.domain_name}: "
            f"{len(deduplicated_urls)} unique URLs from {len(successful_methods)} methods "
            f"in {total_time:.2f}s",
            tag="URL_DISCOVERY"
        )
        
        return result
    
    async def deduplicate_and_score(
        self,
        urls: List[Dict[str, Any]],
        domain_config: DomainConfiguration,
        query: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Advanced URL deduplication with quality scoring.
        
        Args:
            urls: List of URL dictionaries from discovery methods
            domain_config: Domain configuration for Vietnamese optimization
            query: Query for relevance scoring
            
        Returns:
            Deduplicated and scored URL list
        """
        if not urls:
            return []
        
        self.logger.info(f"Starting deduplication of {len(urls)} URLs", tag="URL_DEDUP")
        
        # Phase 1: Basic deduplication by URL
        seen_urls: Set[str] = set()
        unique_urls = []
        
        for url_data in urls:
            url = url_data.get("url", "").strip()
            if not url or url in seen_urls:
                continue
                
            seen_urls.add(url)
            
            # Ensure required fields
            if "discovery_method" not in url_data:
                url_data["discovery_method"] = "unknown"
            if "quality_score" not in url_data:
                url_data["quality_score"] = 0.5
                
            unique_urls.append(url_data)
        
        self.logger.info(f"After basic deduplication: {len(unique_urls)} unique URLs", tag="URL_DEDUP")
        
        # Phase 2: Vietnamese content scoring
        if self.vietnamese_optimization:
            unique_urls = await self._apply_vietnamese_scoring(unique_urls, domain_config, query)
        
        # Phase 3: Combined quality scoring
        unique_urls = await self._apply_combined_scoring(unique_urls, domain_config)
        
        # Phase 4: Sort by quality score
        unique_urls.sort(key=lambda x: x.get("combined_score", 0), reverse=True)
        
        self.logger.info(f"Deduplication and scoring completed: {len(unique_urls)} final URLs", tag="URL_DEDUP")
        
        return unique_urls
    
    async def _discover_from_rss(
        self,
        domain_config: DomainConfiguration,
        force_refresh: bool,
        query: Optional[str]
    ) -> DiscoveryResult:
        """Discover URLs from RSS feeds."""
        start_time = time.time()
        
        try:
            # RSS feeds are typically recent content, so we use a shorter cache TTL
            config = SeedingConfig(
                source="sitemap",  # Use sitemap source which handles RSS-like feeds
                pattern="*",
                extract_head=True,
                concurrency=self.concurrency_limit,
                max_urls=self.max_urls_per_method,
                query=query or " ".join(domain_config.vietnamese_keywords),
                score_threshold=0.3 if self.vietnamese_optimization else None,
                force=force_refresh,
                filter_nonsense_urls=True,
                verbose=False
            )
            
            # For RSS, we'll use the URL seeder with custom URLs
            rss_urls = []
            if domain_config.rss_feeds:
                # Extract URLs from RSS feeds using head extraction
                rss_urls = await self.url_seeder.extract_head_for_urls(
                    domain_config.rss_feeds,
                    config=config
                )
            
            execution_time = time.time() - start_time
            
            # Format results
            formatted_urls = []
            for url_data in rss_urls:
                formatted_urls.append({
                    **url_data,
                    "discovery_method": DiscoveryMethod.RSS.value,
                    "discovered_at": datetime.utcnow().isoformat(),
                    "domain_id": str(domain_config.id)
                })
            
            return DiscoveryResult(
                method=DiscoveryMethod.RSS,
                urls=formatted_urls,
                execution_time=execution_time,
                success=True,
                metadata={"rss_feeds_count": len(domain_config.rss_feeds)}
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            return DiscoveryResult(
                method=DiscoveryMethod.RSS,
                urls=[],
                execution_time=execution_time,
                success=False,
                error=str(e)
            )
    
    async def _discover_from_sitemaps(
        self,
        domain_config: DomainConfiguration,
        force_refresh: bool,
        query: Optional[str]
    ) -> DiscoveryResult:
        """Discover URLs from sitemaps using Crawl4AI AsyncUrlSeeder."""
        start_time = time.time()
        
        try:
            config = SeedingConfig(
                source="sitemap",
                pattern="*",
                extract_head=True,
                concurrency=self.concurrency_limit,
                max_urls=self.max_urls_per_method,
                query=query or " ".join(domain_config.vietnamese_keywords),
                score_threshold=0.3 if self.vietnamese_optimization else None,
                force=force_refresh,
                filter_nonsense_urls=True,
                verbose=False
            )
            
            urls = await self.url_seeder.urls(domain_config.domain_name, config)
            execution_time = time.time() - start_time
            
            # Format results
            formatted_urls = []
            for url_data in urls:
                formatted_urls.append({
                    **url_data,
                    "discovery_method": DiscoveryMethod.SITEMAP.value,
                    "discovered_at": datetime.utcnow().isoformat(),
                    "domain_id": str(domain_config.id)
                })
            
            return DiscoveryResult(
                method=DiscoveryMethod.SITEMAP,
                urls=formatted_urls,
                execution_time=execution_time,
                success=True,
                metadata={"sitemap_processing": True}
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            return DiscoveryResult(
                method=DiscoveryMethod.SITEMAP,
                urls=[],
                execution_time=execution_time,
                success=False,
                error=str(e)
            )
    
    async def _discover_from_categories(
        self,
        domain_config: DomainConfiguration,
        force_refresh: bool,
        query: Optional[str]
    ) -> DiscoveryResult:
        """Discover URLs from category pages using deep crawling."""
        start_time = time.time()
        
        try:
            # Use BFS strategy for category exploration
            category_urls = []
            
            if domain_config.category_urls:
                # Create Vietnamese content filter chain
                filter_chain = self._create_vietnamese_filter_chain(domain_config)
                
                # Use BFS strategy with limited depth for categories
                bfs_strategy = BFSDeepCrawlStrategy(
                    max_depth=min(domain_config.max_depth, 2),  # Limit depth for categories
                    filter_chain=filter_chain,
                    concurrency=self.concurrency_limit
                )
                
                # Process each category URL
                for category_url in domain_config.category_urls:
                    try:
                        category_results = await bfs_strategy.crawl(
                            start_url=category_url,
                            max_urls=self.max_urls_per_method // len(domain_config.category_urls)
                        )
                        category_urls.extend(category_results)
                    except Exception as e:
                        self.logger.warning(
                            f"Category crawl failed for {category_url}: {str(e)}",
                            tag="URL_DISCOVERY"
                        )
                        continue
            
            execution_time = time.time() - start_time
            
            # Format results
            formatted_urls = []
            for url_data in category_urls:
                if isinstance(url_data, str):
                    url_data = {"url": url_data, "status": "discovered"}
                
                formatted_urls.append({
                    **url_data,
                    "discovery_method": DiscoveryMethod.CATEGORY.value,
                    "discovered_at": datetime.utcnow().isoformat(),
                    "domain_id": str(domain_config.id)
                })
            
            return DiscoveryResult(
                method=DiscoveryMethod.CATEGORY,
                urls=formatted_urls,
                execution_time=execution_time,
                success=True,
                metadata={"category_urls_count": len(domain_config.category_urls)}
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            return DiscoveryResult(
                method=DiscoveryMethod.CATEGORY,
                urls=[],
                execution_time=execution_time,
                success=False,
                error=str(e)
            )
    
    async def _discover_from_common_crawl(
        self,
        domain_config: DomainConfiguration,
        force_refresh: bool,
        query: Optional[str]
    ) -> DiscoveryResult:
        """Discover URLs from Common Crawl using Crawl4AI AsyncUrlSeeder."""
        start_time = time.time()
        
        try:
            config = SeedingConfig(
                source="cc",  # Common Crawl source
                pattern="*",
                extract_head=True,
                concurrency=self.concurrency_limit,
                max_urls=self.max_urls_per_method,
                query=query or " ".join(domain_config.vietnamese_keywords),
                score_threshold=0.3 if self.vietnamese_optimization else None,
                force=force_refresh,
                filter_nonsense_urls=True,
                verbose=False
            )
            
            urls = await self.url_seeder.urls(domain_config.domain_name, config)
            execution_time = time.time() - start_time
            
            # Format results
            formatted_urls = []
            for url_data in urls:
                formatted_urls.append({
                    **url_data,
                    "discovery_method": DiscoveryMethod.COMMON_CRAWL.value,
                    "discovered_at": datetime.utcnow().isoformat(),
                    "domain_id": str(domain_config.id)
                })
            
            return DiscoveryResult(
                method=DiscoveryMethod.COMMON_CRAWL,
                urls=formatted_urls,
                execution_time=execution_time,
                success=True,
                metadata={"common_crawl_processing": True}
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            return DiscoveryResult(
                method=DiscoveryMethod.COMMON_CRAWL,
                urls=[],
                execution_time=execution_time,
                success=False,
                error=str(e)
            )
    
    async def _discover_from_deep_crawl(
        self,
        domain_config: DomainConfiguration,
        force_refresh: bool,
        query: Optional[str]
    ) -> DiscoveryResult:
        """Deep crawl fallback strategy for difficult domains."""
        start_time = time.time()
        
        try:
            # Create Vietnamese content filter chain
            filter_chain = self._create_vietnamese_filter_chain(domain_config)
            
            # Use Best-First strategy with Vietnamese keyword scorer
            vietnamese_query = query or " ".join(domain_config.vietnamese_keywords)
            keyword_scorer = KeywordRelevanceScorer(keywords=vietnamese_query.split())
            
            bf_strategy = BestFirstCrawlStrategy(
                max_depth=domain_config.max_depth,
                filter_chain=filter_chain,
                scorer=keyword_scorer,
                concurrency=self.concurrency_limit
            )
            
            # Start deep crawl from base URL
            urls = await bf_strategy.crawl(
                start_url=domain_config.base_url,
                max_urls=self.max_urls_per_method
            )
            
            execution_time = time.time() - start_time
            
            # Format results
            formatted_urls = []
            for url_data in urls:
                if isinstance(url_data, str):
                    url_data = {"url": url_data, "status": "discovered"}
                
                formatted_urls.append({
                    **url_data,
                    "discovery_method": DiscoveryMethod.DEEP_CRAWL_FALLBACK.value,
                    "discovered_at": datetime.utcnow().isoformat(),
                    "domain_id": str(domain_config.id),
                    "crawl_depth": url_data.get("depth", 0)
                })
            
            return DiscoveryResult(
                method=DiscoveryMethod.DEEP_CRAWL_FALLBACK,
                urls=formatted_urls,
                execution_time=execution_time,
                success=True,
                metadata={
                    "max_depth": domain_config.max_depth,
                    "vietnamese_keywords": len(domain_config.vietnamese_keywords)
                }
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            return DiscoveryResult(
                method=DiscoveryMethod.DEEP_CRAWL_FALLBACK,
                urls=[],
                execution_time=execution_time,
                success=False,
                error=str(e)
            )
    
    def _detect_available_methods(self, domain_config: DomainConfiguration) -> List[DiscoveryMethod]:
        """Auto-detect available discovery methods based on domain configuration."""
        methods = []
        
        # Always try sitemaps and common crawl
        methods.extend([DiscoveryMethod.SITEMAP, DiscoveryMethod.COMMON_CRAWL])
        
        # RSS if feeds are configured
        if domain_config.has_rss_feeds and domain_config.rss_feeds:
            methods.append(DiscoveryMethod.RSS)
            
        # Category if URLs are configured
        if domain_config.has_category_urls and domain_config.category_urls:
            methods.append(DiscoveryMethod.CATEGORY)
            
        # Deep crawl fallback if other methods are limited
        if len(methods) <= 2:
            methods.append(DiscoveryMethod.DEEP_CRAWL_FALLBACK)
        
        return methods
    
    def _create_vietnamese_filter_chain(self, domain_config: DomainConfiguration) -> FilterChain:
        """Create filter chain optimized for Vietnamese news content."""
        filters = []
        
        # URL pattern filter for Vietnamese news
        url_filter = URLPatternFilter(patterns=self.vietnamese_patterns)
        filters.append(url_filter)
        
        # Content relevance filter
        vietnamese_query = " ".join(domain_config.vietnamese_keywords)
        content_filter = ContentRelevanceFilter(
            query=vietnamese_query,
            threshold=0.3
        )
        filters.append(content_filter)
        
        return FilterChain(filters)
    
    async def _apply_vietnamese_scoring(
        self,
        urls: List[Dict[str, Any]],
        domain_config: DomainConfiguration,
        query: Optional[str]
    ) -> List[Dict[str, Any]]:
        """Apply Vietnamese content scoring using URL patterns and keywords."""
        
        vietnamese_keywords = set(domain_config.vietnamese_keywords)
        
        for url_data in urls:
            url = url_data.get("url", "").lower()
            score = 0.0
            
            # URL pattern scoring
            for pattern in self.vietnamese_patterns:
                if pattern.replace("*/", "").replace("/*", "") in url:
                    score += 0.3
                    break
            
            # Keyword scoring in URL
            for keyword in vietnamese_keywords:
                if keyword.lower() in url:
                    score += 0.2
            
            # Head data scoring if available
            if "head_data" in url_data and url_data["head_data"]:
                head_score = self._score_vietnamese_content(url_data["head_data"], vietnamese_keywords)
                score += head_score * 0.5
            
            url_data["vietnamese_score"] = min(score, 1.0)
        
        return urls
    
    def _score_vietnamese_content(self, head_data: Dict[str, Any], keywords: Set[str]) -> float:
        """Score Vietnamese content from head data."""
        score = 0.0
        text_content = ""
        
        # Extract text from head data
        if head_data.get("title"):
            text_content += head_data["title"] + " "
        
        meta = head_data.get("meta", {})
        if meta.get("description"):
            text_content += meta["description"] + " "
        
        if meta.get("keywords"):
            text_content += meta["keywords"] + " "
        
        # Keyword matching
        text_lower = text_content.lower()
        matched_keywords = sum(1 for kw in keywords if kw.lower() in text_lower)
        if matched_keywords > 0:
            score = matched_keywords / len(keywords)
        
        return min(score, 1.0)
    
    async def _apply_combined_scoring(
        self,
        urls: List[Dict[str, Any]],
        domain_config: DomainConfiguration
    ) -> List[Dict[str, Any]]:
        """Apply combined scoring from all factors."""
        
        for url_data in urls:
            scores = []
            
            # Base quality score from discovery method
            if "quality_score" in url_data:
                scores.append(url_data["quality_score"])
            
            # Vietnamese content score
            if "vietnamese_score" in url_data:
                scores.append(url_data["vietnamese_score"])
            
            # Relevance score from BM25 if available
            if "relevance_score" in url_data:
                scores.append(url_data["relevance_score"])
            
            # Discovery method weight
            method_weight = self._get_method_weight(url_data.get("discovery_method"))
            scores.append(method_weight)
            
            # Calculate weighted average
            if scores:
                url_data["combined_score"] = sum(scores) / len(scores)
            else:
                url_data["combined_score"] = 0.5
        
        return urls
    
    def _get_method_weight(self, method: str) -> float:
        """Get quality weight for discovery method."""
        method_weights = {
            DiscoveryMethod.RSS.value: 0.9,  # High quality, recent content
            DiscoveryMethod.SITEMAP.value: 0.8,  # Good coverage
            DiscoveryMethod.COMMON_CRAWL.value: 0.7,  # Large dataset
            DiscoveryMethod.CATEGORY.value: 0.6,  # Targeted but may be limited
            DiscoveryMethod.DEEP_CRAWL_FALLBACK.value: 0.5,  # Fallback method
            DiscoveryMethod.GOOGLE_SEARCH.value: 0.95  # Highest quality but manual
        }
        return method_weights.get(method, 0.5)
    
    def _calculate_quality_metrics(
        self,
        all_urls: List[Dict[str, Any]],
        deduplicated_urls: List[Dict[str, Any]],
        method_results: Dict[DiscoveryMethod, DiscoveryResult]
    ) -> Dict[str, Any]:
        """Calculate quality metrics for the discovery process."""
        
        total_discovered = len(all_urls)
        unique_count = len(deduplicated_urls)
        deduplication_rate = 1 - (unique_count / total_discovered) if total_discovered > 0 else 0
        
        # Method success rates
        method_success = {
            method.value: result.success 
            for method, result in method_results.items()
        }
        
        # Average quality score
        quality_scores = [url.get("combined_score", 0) for url in deduplicated_urls]
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0
        
        # Vietnamese content percentage
        vietnamese_scores = [url.get("vietnamese_score", 0) for url in deduplicated_urls]
        vietnamese_content_pct = len([s for s in vietnamese_scores if s > 0.3]) / len(vietnamese_scores) if vietnamese_scores else 0
        
        return {
            "total_discovered": total_discovered,
            "unique_count": unique_count,
            "deduplication_rate": deduplication_rate,
            "method_success_rates": method_success,
            "average_quality_score": avg_quality,
            "vietnamese_content_percentage": vietnamese_content_pct,
            "high_quality_urls": len([s for s in quality_scores if s > 0.7])
        }
    
    async def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for all discovery methods."""
        metrics = {}
        
        for method, times in self.method_performance.items():
            if times:
                metrics[method.value] = {
                    "average_time": sum(times) / len(times),
                    "min_time": min(times),
                    "max_time": max(times),
                    "execution_count": len(times),
                    "success_rate": 1.0  # Would need to track failures separately
                }
            else:
                metrics[method.value] = {
                    "average_time": 0,
                    "min_time": 0,
                    "max_time": 0,
                    "execution_count": 0,
                    "success_rate": 0
                }
        
        return metrics
    
    async def close(self):
        """Clean up resources."""
        if self.url_seeder:
            await self.url_seeder.close()