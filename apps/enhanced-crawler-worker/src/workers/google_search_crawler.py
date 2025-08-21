"""
Google Search Crawler - Manual trigger only for advanced URL discovery

This module provides Google Search API integration for Vietnamese news domains
with manual trigger capability from admin interface only.

Features:
- Search API query execution với Vietnamese keywords (on admin request)
- Date-filtered searches cho historical data discovery (admin interface initiated)  
- Search result processing và URL extraction (triggered by user action)
- Manual trigger API endpoint integration với admin interface
- Google API usage monitoring và cost tracking cho manual requests
- Vietnamese search query optimization
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote, unquote
from dataclasses import dataclass

# Import Crawl4AI components
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'crawl4ai-main'))

from crawl4ai.crawlers.google_search.crawler import GoogleSearchCrawler as BaseCrawler
from crawl4ai.async_logger import AsyncLogger

@dataclass
class GoogleSearchConfig:
    """Configuration for Google Search API requests."""
    domain: str
    keywords: List[str]
    site_restrict: bool = True  # Restrict to specific domain
    max_results: int = 100
    date_range: Optional[Tuple[datetime, datetime]] = None
    language: str = "vi"  # Vietnamese
    region: str = "VN"  # Vietnam
    search_type: str = "text"  # "text" or "image"
    safe_search: bool = True
    include_snippets: bool = True
    
@dataclass
class SearchResult:
    """Represents a single search result."""
    title: str
    url: str
    snippet: Optional[str] = None
    published_date: Optional[str] = None
    source: Optional[str] = None
    relevance_score: float = 0.0
    vietnamese_score: float = 0.0

@dataclass
class GoogleSearchResult:
    """Result from Google Search operation."""
    domain: str
    query: str
    success: bool
    results: List[SearchResult]
    total_results: int
    search_time: float
    api_cost_estimate: float
    suggested_queries: List[str] = None
    top_stories: List[Dict[str, Any]] = None
    error: Optional[str] = None
    
    def __post_init__(self):
        if self.suggested_queries is None:
            self.suggested_queries = []
        if self.top_stories is None:
            self.top_stories = []

class GoogleSearchCrawler:
    """
    Google Search crawler for Vietnamese news domains (MANUAL TRIGGER ONLY).
    
    This crawler is designed to be triggered manually from admin interface
    and provides intelligent Google Search integration with Vietnamese optimization.
    """
    
    def __init__(
        self,
        logger: Optional[AsyncLogger] = None,
        api_key: Optional[str] = None,
        enable_api_usage: bool = False
    ):
        self.logger = logger or AsyncLogger()
        self.api_key = api_key
        self.enable_api_usage = enable_api_usage
        
        # Initialize Crawl4AI Google Search crawler
        self.base_crawler = BaseCrawler()
        
        # Vietnamese search optimization
        self.vietnamese_keywords = [
            "tin tức", "báo chí", "thời sự", "hôm nay", "mới nhất",
            "kinh tế", "xã hội", "chính trị", "thể thao", "pháp luật",
            "giáo dục", "sức khỏe", "công nghệ", "môi trường"
        ]
        
        # Search query templates for Vietnamese news
        self.search_templates = {
            "general_news": 'site:{domain} ({keywords}) (tin tức OR báo chí OR thời sự)',
            "recent_news": 'site:{domain} ({keywords}) after:{date}',
            "category_news": 'site:{domain} "{category}" ({keywords})',
            "date_range": 'site:{domain} ({keywords}) after:{start_date} before:{end_date}'
        }
        
        # API usage tracking
        self.api_usage_stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_results_returned": 0,
            "estimated_total_cost": 0.0,
            "last_request_time": None,
            "monthly_usage": 0,
            "daily_usage": 0
        }
        
        # Rate limiting (respect Google's terms)
        self.rate_limit_delay = 1.0  # 1 second between requests
        self.last_request_time = 0.0
    
    async def manual_search_trigger(
        self,
        config: GoogleSearchConfig,
        admin_user_id: str,
        request_reason: str = "Manual domain analysis"
    ) -> GoogleSearchResult:
        """
        Execute manual Google Search (ADMIN TRIGGERED ONLY).
        
        This method should only be called from admin interface with proper
        authentication and justification.
        
        Args:
            config: Search configuration
            admin_user_id: ID of admin user triggering the search
            request_reason: Reason for manual search request
            
        Returns:
            GoogleSearchResult with discovered URLs and metadata
        """
        # Log manual trigger for audit trail
        self.logger.info(
            f"MANUAL GOOGLE SEARCH TRIGGERED by admin {admin_user_id} for domain {config.domain}",
            tag="GOOGLE_SEARCH"
        )
        self.logger.info(f"Search reason: {request_reason}", tag="GOOGLE_SEARCH")
        
        start_time = time.time()
        
        try:
            # Rate limiting enforcement
            await self._enforce_rate_limit()
            
            # Build search query
            search_query = await self._build_vietnamese_query(config)
            
            self.logger.info(f"Executing Google Search: {search_query}", tag="GOOGLE_SEARCH")
            
            # Execute search using Crawl4AI Google Search crawler
            search_results = await self._execute_search(search_query, config)
            
            # Process and filter results
            processed_results = await self._process_search_results(search_results, config)
            
            # Apply Vietnamese scoring
            vietnamese_results = await self._apply_vietnamese_scoring(processed_results, config)
            
            # Calculate costs and update tracking
            execution_time = time.time() - start_time
            estimated_cost = self._calculate_api_cost(len(vietnamese_results))
            
            result = GoogleSearchResult(
                domain=config.domain,
                query=search_query,
                success=True,
                results=vietnamese_results,
                total_results=len(vietnamese_results),
                search_time=execution_time,
                api_cost_estimate=estimated_cost,
                suggested_queries=search_results.get("suggested_queries", []),
                top_stories=search_results.get("top_stories", [])
            )
            
            # Update usage stats
            self._update_usage_stats(result)
            
            # Log completion with audit info
            self.logger.info(
                f"Manual Google Search completed: {len(vietnamese_results)} results in {execution_time:.2f}s "
                f"(estimated cost: ${estimated_cost:.4f})",
                tag="GOOGLE_SEARCH"
            )
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = str(e)
            
            self.logger.error(
                f"Manual Google Search failed for {config.domain}: {error_msg}",
                tag="GOOGLE_SEARCH"
            )
            
            # Update failure stats
            self.api_usage_stats["failed_requests"] += 1
            
            return GoogleSearchResult(
                domain=config.domain,
                query="",
                success=False,
                results=[],
                total_results=0,
                search_time=execution_time,
                api_cost_estimate=0.0,
                error=error_msg
            )
    
    async def bulk_domain_search(
        self,
        domains: List[str],
        base_config: GoogleSearchConfig,
        admin_user_id: str,
        max_concurrent: int = 3
    ) -> Dict[str, GoogleSearchResult]:
        """
        Execute bulk manual search for multiple domains (ADMIN ONLY).
        
        Args:
            domains: List of domains to search
            base_config: Base configuration to use for all searches
            admin_user_id: Admin user ID for audit trail
            max_concurrent: Maximum concurrent searches
            
        Returns:
            Dictionary mapping domains to search results
        """
        self.logger.info(
            f"BULK GOOGLE SEARCH TRIGGERED by admin {admin_user_id} for {len(domains)} domains",
            tag="GOOGLE_SEARCH"
        )
        
        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def search_single_domain(domain: str):
            async with semaphore:
                domain_config = GoogleSearchConfig(
                    domain=domain,
                    keywords=base_config.keywords,
                    site_restrict=base_config.site_restrict,
                    max_results=base_config.max_results,
                    date_range=base_config.date_range,
                    language=base_config.language,
                    region=base_config.region
                )
                
                return domain, await self.manual_search_trigger(
                    domain_config, 
                    admin_user_id, 
                    f"Bulk domain analysis for {domain}"
                )
        
        # Execute searches concurrently
        tasks = [search_single_domain(domain) for domain in domains]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        domain_results = {}
        successful_searches = 0
        
        for result in results:
            if isinstance(result, Exception):
                self.logger.error(f"Bulk search task failed: {str(result)}", tag="GOOGLE_SEARCH")
                continue
            
            domain, search_result = result
            domain_results[domain] = search_result
            
            if search_result.success:
                successful_searches += 1
        
        self.logger.info(
            f"Bulk Google Search completed: {successful_searches}/{len(domains)} successful",
            tag="GOOGLE_SEARCH"
        )
        
        return domain_results
    
    async def _build_vietnamese_query(self, config: GoogleSearchConfig) -> str:
        """Build optimized search query for Vietnamese content."""
        
        # Base keywords
        keywords = " OR ".join([f'"{kw}"' for kw in config.keywords])
        
        # Add Vietnamese context keywords
        vietnamese_context = " OR ".join([f'"{vn_kw}"' for vn_kw in self.vietnamese_keywords[:5]])
        
        # Choose appropriate template
        if config.date_range:
            start_date, end_date = config.date_range
            template = self.search_templates["date_range"]
            query = template.format(
                domain=config.domain,
                keywords=keywords,
                start_date=start_date.strftime("%Y-%m-%d"),
                end_date=end_date.strftime("%Y-%m-%d")
            )
        elif config.date_range and (datetime.utcnow() - config.date_range[0]).days <= 7:
            # Recent news
            template = self.search_templates["recent_news"]
            query = template.format(
                domain=config.domain,
                keywords=keywords,
                date=config.date_range[0].strftime("%Y-%m-%d")
            )
        else:
            # General news search
            template = self.search_templates["general_news"]
            query = template.format(
                domain=config.domain,
                keywords=keywords
            )
        
        # Add Vietnamese context if not already included
        if not any(vn_kw in " ".join(config.keywords) for vn_kw in self.vietnamese_keywords):
            query = f"({query}) AND ({vietnamese_context})"
        
        # Add language and region restrictions
        query += f" lang:{config.language}"
        
        return query
    
    async def _execute_search(self, query: str, config: GoogleSearchConfig) -> Dict[str, Any]:
        """Execute the actual Google Search using Crawl4AI."""
        
        try:
            # Use Crawl4AI Google Search crawler
            raw_result = await self.base_crawler.run(
                query=query,
                search_type=config.search_type,
                page_length=min(config.max_results, 100),  # Limit to reasonable number
                delay=2  # Respectful delay
            )
            
            # Parse JSON result
            result_data = json.loads(raw_result)
            
            if "error" in result_data:
                raise Exception(result_data["error"])
            
            return result_data
            
        except Exception as e:
            self.logger.error(f"Google Search execution failed: {str(e)}", tag="GOOGLE_SEARCH")
            raise
    
    async def _process_search_results(
        self, 
        raw_results: Dict[str, Any], 
        config: GoogleSearchConfig
    ) -> List[SearchResult]:
        """Process raw search results into structured format."""
        
        processed_results = []
        
        # Process organic results
        organic_results = raw_results.get("organic_schema", [])
        if isinstance(organic_results, list):
            for item in organic_results:
                if isinstance(item, dict):
                    result = SearchResult(
                        title=item.get("title", ""),
                        url=item.get("link", ""),
                        snippet=item.get("snippet", ""),
                        published_date=item.get("date", ""),
                        source=config.domain
                    )
                    processed_results.append(result)
        
        # Process top stories if available
        top_stories = raw_results.get("top_stories_schema", [])
        if isinstance(top_stories, list):
            for item in top_stories:
                if isinstance(item, dict):
                    result = SearchResult(
                        title=item.get("title", ""),
                        url=item.get("link", ""),
                        snippet="",  # Top stories usually don't have snippets
                        published_date=item.get("date", ""),
                        source=item.get("source", config.domain)
                    )
                    processed_results.append(result)
        
        # Filter out invalid results
        valid_results = []
        for result in processed_results:
            if result.url and result.title:
                # Ensure URL belongs to target domain if site restriction is enabled
                if config.site_restrict:
                    if config.domain.lower() in result.url.lower():
                        valid_results.append(result)
                else:
                    valid_results.append(result)
        
        return valid_results
    
    async def _apply_vietnamese_scoring(
        self,
        results: List[SearchResult],
        config: GoogleSearchConfig
    ) -> List[SearchResult]:
        """Apply Vietnamese content scoring to search results."""
        
        for result in results:
            score = 0.0
            
            # Score based on title content
            title_lower = result.title.lower()
            title_matches = sum(1 for keyword in self.vietnamese_keywords if keyword in title_lower)
            if title_matches > 0:
                score += (title_matches / len(self.vietnamese_keywords)) * 0.4
            
            # Score based on snippet content
            if result.snippet:
                snippet_lower = result.snippet.lower()
                snippet_matches = sum(1 for keyword in self.vietnamese_keywords if keyword in snippet_lower)
                if snippet_matches > 0:
                    score += (snippet_matches / len(self.vietnamese_keywords)) * 0.3
            
            # Score based on URL structure
            url_lower = result.url.lower()
            if any(pattern in url_lower for pattern in ['.vn/', 'vietnam', '/tin-', '/bao-']):
                score += 0.3
            
            # Relevance score based on original query keywords
            query_matches = sum(1 for keyword in config.keywords if keyword.lower() in title_lower)
            result.relevance_score = query_matches / len(config.keywords) if config.keywords else 0
            
            result.vietnamese_score = min(score, 1.0)
        
        # Sort by combined scores
        results.sort(key=lambda x: (x.vietnamese_score, x.relevance_score), reverse=True)
        
        return results
    
    async def _enforce_rate_limit(self):
        """Enforce rate limiting to respect Google's terms."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.rate_limit_delay:
            sleep_time = self.rate_limit_delay - time_since_last
            self.logger.debug(f"Rate limiting: sleeping {sleep_time:.2f}s", tag="GOOGLE_SEARCH")
            await asyncio.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def _calculate_api_cost(self, result_count: int) -> float:
        """Calculate estimated API cost for the search."""
        # Estimated cost based on typical Google Search API pricing
        # This is a rough estimate - actual costs may vary
        base_cost_per_query = 0.005  # $0.005 per query
        cost_per_result = 0.001      # $0.001 per result returned
        
        total_cost = base_cost_per_query + (result_count * cost_per_result)
        return total_cost
    
    def _update_usage_stats(self, result: GoogleSearchResult):
        """Update API usage statistics."""
        self.api_usage_stats["total_requests"] += 1
        
        if result.success:
            self.api_usage_stats["successful_requests"] += 1
            self.api_usage_stats["total_results_returned"] += result.total_results
        else:
            self.api_usage_stats["failed_requests"] += 1
        
        self.api_usage_stats["estimated_total_cost"] += result.api_cost_estimate
        self.api_usage_stats["last_request_time"] = datetime.utcnow().isoformat()
        
        # Update daily/monthly counters (simplified)
        self.api_usage_stats["daily_usage"] += 1
        self.api_usage_stats["monthly_usage"] += 1
    
    def get_usage_statistics(self) -> Dict[str, Any]:
        """Get current API usage statistics."""
        stats = self.api_usage_stats.copy()
        
        # Add success rate
        total_requests = stats["total_requests"]
        if total_requests > 0:
            stats["success_rate"] = stats["successful_requests"] / total_requests
            stats["average_results_per_query"] = stats["total_results_returned"] / stats["successful_requests"] if stats["successful_requests"] > 0 else 0
            stats["average_cost_per_query"] = stats["estimated_total_cost"] / total_requests
        else:
            stats["success_rate"] = 0
            stats["average_results_per_query"] = 0
            stats["average_cost_per_query"] = 0
        
        return stats
    
    def reset_usage_stats(self):
        """Reset usage statistics (for new billing period)."""
        self.logger.info("Resetting Google Search API usage statistics", tag="GOOGLE_SEARCH")
        
        self.api_usage_stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_results_returned": 0,
            "estimated_total_cost": 0.0,
            "last_request_time": None,
            "monthly_usage": 0,
            "daily_usage": 0
        }
    
    def is_usage_limit_exceeded(self, daily_limit: int = 100, monthly_limit: int = 3000) -> Dict[str, bool]:
        """Check if usage limits are being approached or exceeded."""
        return {
            "daily_limit_exceeded": self.api_usage_stats["daily_usage"] >= daily_limit,
            "monthly_limit_exceeded": self.api_usage_stats["monthly_usage"] >= monthly_limit,
            "daily_warning": self.api_usage_stats["daily_usage"] >= (daily_limit * 0.8),
            "monthly_warning": self.api_usage_stats["monthly_usage"] >= (monthly_limit * 0.8)
        }