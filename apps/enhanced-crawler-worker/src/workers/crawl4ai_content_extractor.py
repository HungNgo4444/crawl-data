"""
Advanced Crawl4AI Content Extractor
Universal content extraction using multiple strategies with intelligent fallback.
Based on Crawl4AI official documentation and best practices.
"""

import asyncio
import hashlib
import json
import os
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from urllib.parse import urlparse
from dataclasses import dataclass, field
import logging

# Crawl4AI imports
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from crawl4ai.extraction_strategy import (
    JsonCssExtractionStrategy, 
    LLMExtractionStrategy,
    NoExtractionStrategy
)
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
from crawl4ai.content_filter_strategy import PruningContentFilter, BM25ContentFilter
from crawl4ai.chunking_strategy import RegexChunking
from bs4 import BeautifulSoup
from lxml import html as lxml_html
import re


# Configuration constants
class ExtractionConfig:
    """Configuration for extraction operations."""
    # Timeouts
    PAGE_TIMEOUT_MS = 30000  # 30 seconds for complex sites
    QUICK_TIMEOUT_MS = 10000  # 10 seconds for quick extraction
    
    # Content thresholds
    MIN_CONTENT_LENGTH = 100
    MAX_CONTENT_LENGTH = 500000
    MIN_WORD_COUNT = 20
    
    # Extraction settings
    MAX_CONCURRENT = 10
    CACHE_TTL = 86400  # 24 hours
    
    # Content filtering
    PRUNING_THRESHOLD = 0.3  # Lower = more content kept
    BM25_KEYWORDS = ["article", "content", "post", "news", "story"]


@dataclass
class ExtractedArticle:
    """Represents an extracted article with all metadata."""
    url: str
    title: str
    content: str
    author: Optional[str] = None
    publish_date: Optional[str] = None
    category: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    summary: Optional[str] = None
    image_url: Optional[str] = None
    images: List[str] = field(default_factory=list)
    
    # Extraction metadata
    extraction_method: str = "unknown"
    extraction_time: float = 0.0
    content_length: int = 0
    word_count: int = 0
    success: bool = True
    error: Optional[str] = None
    cached: bool = False
    
    # Additional metadata
    links_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Calculate derived fields."""
        if self.content:
            self.content_length = len(self.content)
            self.word_count = len(self.content.split())


@dataclass 
class ExtractionResult:
    """Result of extraction operation."""
    success: bool
    articles: List[ExtractedArticle]
    total_urls: int
    successful: int
    failed: int
    execution_time: float
    errors: List[str] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)


class AdvancedCrawl4AIExtractor:
    """
    Advanced content extractor using Crawl4AI with multiple strategies.
    
    Features:
    - Multiple extraction strategies with intelligent fallback
    - Advanced metadata extraction
    - Content deduplication
    - Performance optimization
    - Caching support
    """
    
    def __init__(
        self,
        logger: Optional[logging.Logger] = None,
        cache_dir: str = "./cache/crawl4ai",
        enable_llm: bool = False,
        llm_provider: Optional[str] = None,
        llm_api_key: Optional[str] = None
    ):
        """Initialize the extractor with configuration."""
        self.logger = logger or logging.getLogger(__name__)
        self.cache_dir = cache_dir
        self.enable_llm = enable_llm
        self.llm_provider = llm_provider
        self.llm_api_key = llm_api_key
        
        # Performance tracking
        self.stats = {
            "total_extracted": 0,
            "json_css_success": 0,
            "llm_success": 0,
            "fallback_success": 0,
            "cache_hits": 0,
            "total_time": 0.0
        }
        
        # Content deduplication
        self.content_hashes: Set[str] = set()
        
        # Create cache directory
        os.makedirs(cache_dir, exist_ok=True)
    
    async def extract_urls(
        self,
        urls: List[str],
        max_concurrent: int = ExtractionConfig.MAX_CONCURRENT,
        use_cache: bool = True
    ) -> ExtractionResult:
        """
        Extract content from multiple URLs concurrently.
        
        Args:
            urls: List of URLs to extract
            max_concurrent: Maximum concurrent extractions
            use_cache: Whether to use caching
            
        Returns:
            ExtractionResult with all extracted articles
        """
        start_time = time.time()
        
        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def extract_with_limit(url: str) -> Optional[ExtractedArticle]:
            async with semaphore:
                return await self._extract_single_url(url, use_cache)
        
        # Extract all URLs concurrently
        tasks = [extract_with_limit(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        articles = []
        errors = []
        successful = 0
        failed = 0
        
        for url, result in zip(urls, results):
            if isinstance(result, Exception):
                failed += 1
                errors.append(f"{url}: {str(result)}")
                self.logger.error(f"Failed to extract {url}: {result}")
            elif result:
                articles.append(result)
                successful += 1
                if result.success:
                    self.stats["total_extracted"] += 1
            else:
                failed += 1
                errors.append(f"{url}: No content extracted")
        
        # Remove duplicates
        articles = self._deduplicate_articles(articles)
        
        execution_time = time.time() - start_time
        self.stats["total_time"] += execution_time
        
        return ExtractionResult(
            success=successful > 0,
            articles=articles,
            total_urls=len(urls),
            successful=successful,
            failed=failed,
            execution_time=execution_time,
            errors=errors,
            stats=self._get_stats_summary()
        )
    
    async def _extract_single_url(
        self,
        url: str,
        use_cache: bool = True
    ) -> Optional[ExtractedArticle]:
        """
        Extract content from a single URL using multiple strategies.
        
        Strategy order:
        1. Check cache (if enabled)
        2. Try JsonCssExtractionStrategy (structural extraction)
        3. Try LLMExtractionStrategy (if enabled)
        4. Fallback to markdown extraction
        """
        start_time = time.time()
        
        try:
            # Check cache first
            if use_cache:
                cached = await self._get_cached_article(url)
                if cached:
                    self.stats["cache_hits"] += 1
                    cached.cached = True
                    return cached
            
            # Browser configuration for news sites
            browser_config = BrowserConfig(
                headless=True,
                extra_args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--disable-web-security",
                    "--disable-features=IsolateOrigins,site-per-process"
                ]
            )
            
            async with AsyncWebCrawler(config=browser_config) as crawler:
                # Try extraction strategies in order
                article = None
                
                # Strategy 1: JsonCssExtractionStrategy (fastest, most accurate for structured content)
                article = await self._try_json_css_extraction(crawler, url)
                
                # Strategy 2: LLM Extraction (if enabled and JsonCSS failed)
                if not article and self.enable_llm:
                    article = await self._try_llm_extraction(crawler, url)
                
                # Strategy 3: Fallback to markdown extraction
                if not article:
                    article = await self._try_markdown_extraction(crawler, url)
                
                if article:
                    article.extraction_time = time.time() - start_time
                    
                    # Cache the result
                    if use_cache:
                        await self._cache_article(article)
                    
                    return article
                
                return None
                
        except Exception as e:
            self.logger.error(f"Error extracting {url}: {e}")
            return ExtractedArticle(
                url=url,
                title="Error",
                content="",
                success=False,
                error=str(e),
                extraction_time=time.time() - start_time
            )
    
    async def _try_json_css_extraction(
        self,
        crawler: AsyncWebCrawler,
        url: str
    ) -> Optional[ExtractedArticle]:
        """
        Try extraction using JsonCssExtractionStrategy with multiple selector fallback.
        Best for structured content like news articles.
        """
        # Define selector groups for each field - try each selector individually
        field_selectors = {
            "title": [
                "h1.title-detail",
                "h1.title-news", 
                "h1.detail-title",
                ".title-detail",
                "h1",
                "meta[property='og:title']"
            ],
            "content": [
                ".fck_detail",
                "article .content",
                "article .entry-content",
                ".article-body",
                ".post-content",
                "main article",
                ".detail-content",
                "#main-detail-body",
                "article"
            ],
            "author": [
                ".author-name",
                "[itemprop='author']",
                ".by-author",
                ".article-author",
                ".author",
                "meta[name='author']"
            ],
            "publish_date": [
                "time[datetime]",
                ".publish-date",
                ".entry-date",
                "meta[property='article:published_time']"
            ],
            "category": [
                ".breadcrumb li:nth-child(2)",
                ".category",
                ".article-category",
                "nav.breadcrumb a:nth-child(2)"
            ],
            "image": [
                "meta[property='og:image']",
                "article img",
                ".article-image img"
            ],
            "summary": [
                "meta[name='description']",
                ".article-summary",
                ".lead"
            ]
        }
        
        # Try each selector group and return best result
        best_result = None
        best_score = 0
        
        for field_name, selectors in field_selectors.items():
            for selector in selectors:
                # Create schema with single selector
                article_schema = {
                    "name": f"{field_name}_extractor",
                    "baseSelector": "body",
                    "fields": [
                        {
                            "name": field_name,
                            "selector": selector,
                            "type": "attribute" if field_name in ["publish_date", "image"] else "text",
                            "attribute": "datetime" if field_name == "publish_date" else ("content" if field_name == "image" else None),
                            "transform": "strip"
                        }
                    ]
                }
                
                try:
                    result = await self._extract_with_schema(crawler, url, article_schema)
                    if result:
                        field_data = result.get(field_name)
                        if field_data and len(str(field_data)) > 10:  # Valid data found
                            # Store this selector as working for this field
                            if not best_result:
                                best_result = {}
                            best_result[field_name] = {
                                "data": field_data,
                                "selector": selector
                            }
                            break  # Found working selector for this field
                except Exception:
                    continue
        
        # If we found some data, create comprehensive extraction with working selectors
        if best_result:
            # Build final schema with proven selectors
            final_fields = []
            for field_name, field_info in best_result.items():
                field_config = {
                    "name": field_name,
                    "selector": field_info["selector"],
                    "type": "attribute" if field_name in ["publish_date", "image"] else "text",
                    "transform": "strip"
                }
                if field_name == "publish_date":
                    field_config["attribute"] = "datetime"
                elif field_name == "image":
                    field_config["attribute"] = "content"
                    
                final_fields.append(field_config)
            
            final_schema = {
                "name": "comprehensive_extractor",
                "baseSelector": "body",
                "fields": final_fields
            }
            
            # Extract with final schema
            result = await self._extract_with_schema(crawler, url, final_schema)
            if result:
                return await self._build_article_from_data(url, result, "json_css")
        
        return None
    
    async def _extract_with_schema(
        self,
        crawler: AsyncWebCrawler,
        url: str,
        schema: dict
    ) -> Optional[dict]:
        """Extract content using a specific schema."""
        try:
            config = CrawlerRunConfig(
                cache_mode=CacheMode.BYPASS,
                extraction_strategy=JsonCssExtractionStrategy(
                    schema=schema,
                    verbose=False
                ),
                page_timeout=ExtractionConfig.QUICK_TIMEOUT_MS,
                wait_until="domcontentloaded",
                excluded_tags=["script", "style", "nav", "footer", "header"]
            )
            
            result = await crawler.arun(url=url, config=config)
            
            if result.success and result.extracted_content:
                try:
                    data = json.loads(result.extracted_content)
                    if isinstance(data, list) and data:
                        data = data[0]
                    return data
                except json.JSONDecodeError:
                    pass
                    
        except Exception:
            pass
        
        return None
    
    async def _build_article_from_data(
        self,
        url: str,
        data: dict,
        method: str
    ) -> Optional[ExtractedArticle]:
        """Build ExtractedArticle from extracted data."""
        content = data.get("content", "")
        title = data.get("title", "")
        
        if content and len(content) >= ExtractionConfig.MIN_CONTENT_LENGTH:
            article = ExtractedArticle(
                url=url,
                title=title,
                content=content,
                author=data.get("author"),
                publish_date=data.get("publish_date"),
                category=data.get("category"),
                summary=data.get("summary"),
                image_url=data.get("image"),
                extraction_method=method
            )
            
            if method == "json_css":
                self.stats["json_css_success"] += 1
            
            self.logger.info(f"{method} extraction successful for {url}")
            return article
        
        return None
    
    async def _try_llm_extraction(
        self,
        crawler: AsyncWebCrawler,
        url: str
    ) -> Optional[ExtractedArticle]:
        """
        Try extraction using LLMExtractionStrategy.
        Best for complex content requiring understanding.
        """
        if not self.llm_provider or not self.llm_api_key:
            return None
        
        try:
            # LLM extraction for articles
            extraction_prompt = """
            Extract the main article content from this webpage.
            
            Return a JSON object with:
            {
                "title": "article title",
                "content": "main article text content",
                "author": "author name if found",
                "publish_date": "publication date if found",
                "category": "article category if found",
                "summary": "brief summary of the article"
            }
            
            Focus on the main article content only, ignore navigation, ads, and other page elements.
            """
            
            llm_strategy = LLMExtractionStrategy(
                provider=self.llm_provider,
                api_token=self.llm_api_key,
                instruction=extraction_prompt,
                schema={
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "content": {"type": "string"},
                        "author": {"type": "string"},
                        "publish_date": {"type": "string"},
                        "category": {"type": "string"},
                        "summary": {"type": "string"}
                    },
                    "required": ["title", "content"]
                }
            )
            
            config = CrawlerRunConfig(
                cache_mode=CacheMode.BYPASS,
                extraction_strategy=llm_strategy,
                page_timeout=ExtractionConfig.PAGE_TIMEOUT_MS,
                wait_until="networkidle"
            )
            
            result = await crawler.arun(url=url, config=config)
            
            if result.success and result.extracted_content:
                data = json.loads(result.extracted_content)
                
                if data.get("content") and len(data["content"]) >= ExtractionConfig.MIN_CONTENT_LENGTH:
                    article = ExtractedArticle(
                        url=url,
                        title=data.get("title", ""),
                        content=data["content"],
                        author=data.get("author"),
                        publish_date=data.get("publish_date"),
                        category=data.get("category"),
                        summary=data.get("summary"),
                        extraction_method="llm"
                    )
                    
                    self.stats["llm_success"] += 1
                    self.logger.info(f"LLM extraction successful for {url}")
                    return article
                    
        except Exception as e:
            self.logger.debug(f"LLM extraction failed for {url}: {e}")
        
        return None
    
    async def _try_markdown_extraction(
        self,
        crawler: AsyncWebCrawler,
        url: str
    ) -> Optional[ExtractedArticle]:
        """
        Fallback extraction using markdown generation.
        Most reliable but may include extra content.
        """
        try:
            config = CrawlerRunConfig(
                cache_mode=CacheMode.BYPASS,
                markdown_generator=DefaultMarkdownGenerator(
                    content_filter=BM25ContentFilter(
                        user_query=" ".join(ExtractionConfig.BM25_KEYWORDS),
                        bm25_threshold=0.5
                    )
                ),
                page_timeout=ExtractionConfig.QUICK_TIMEOUT_MS,
                wait_until="domcontentloaded",
                excluded_tags=["script", "style", "nav", "footer", "header", "aside"],
                word_count_threshold=ExtractionConfig.MIN_WORD_COUNT
            )
            
            result = await crawler.arun(url=url, config=config)
            
            if result.success:
                # Extract content from markdown
                content = ""
                if result.markdown:
                    if hasattr(result.markdown, 'fit_markdown'):
                        content = result.markdown.fit_markdown
                    elif hasattr(result.markdown, 'raw_markdown'):
                        content = result.markdown.raw_markdown
                    else:
                        content = str(result.markdown)
                
                if content and len(content) >= ExtractionConfig.MIN_CONTENT_LENGTH:
                    # Extract metadata from result
                    metadata = result.metadata or {}
                    
                    # Extract images
                    images = []
                    if result.media and result.media.get("images"):
                        images = [img.get("src", "") for img in result.media["images"] if img.get("src")]
                    
                    article = ExtractedArticle(
                        url=url,
                        title=metadata.get("title"),
                        content=content[:ExtractionConfig.MAX_CONTENT_LENGTH],
                        author=metadata.get("author"),
                        publish_date=metadata.get("article:published_time"),
                        category=None,
                        summary=self._generate_summary(content),
                        image_url=metadata.get("og:image") or (images[0] if images else None),
                        images=images,
                        extraction_method="markdown",
                        links_count=len(result.links.get("internal", [])) + len(result.links.get("external", [])) if result.links else 0
                    )
                    
                    self.stats["fallback_success"] += 1
                    self.logger.info(f"Markdown extraction successful for {url}")
                    return article
                    
        except Exception as e:
            self.logger.debug(f"Markdown extraction failed for {url}: {e}")
        
        return None
    
    
    def _generate_summary(self, content: str, max_length: int = 200) -> str:
        """Generate a simple summary from content."""
        if not content:
            return ""
        
        # Take first few sentences
        sentences = re.split(r'[.!?]\s+', content)
        summary = ""
        
        for sentence in sentences[:3]:
            if len(summary) + len(sentence) < max_length:
                summary += sentence + ". "
            else:
                break
        
        return summary.strip()
    
    def _deduplicate_articles(self, articles: List[ExtractedArticle]) -> List[ExtractedArticle]:
        """Remove duplicate articles based on content hash."""
        unique_articles = []
        
        for article in articles:
            if article.content:
                content_hash = hashlib.md5(article.content.encode()).hexdigest()
                if content_hash not in self.content_hashes:
                    self.content_hashes.add(content_hash)
                    unique_articles.append(article)
        
        return unique_articles
    
    async def _get_cached_article(self, url: str) -> Optional[ExtractedArticle]:
        """Get cached article if available."""
        cache_key = hashlib.md5(url.encode()).hexdigest()
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.json")
        
        try:
            if os.path.exists(cache_file):
                # Check if cache is not expired
                if time.time() - os.path.getmtime(cache_file) < ExtractionConfig.CACHE_TTL:
                    with open(cache_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        return ExtractedArticle(**data)
        except Exception as e:
            self.logger.debug(f"Cache read error for {url}: {e}")
        
        return None
    
    async def _cache_article(self, article: ExtractedArticle):
        """Cache an extracted article."""
        cache_key = hashlib.md5(article.url.encode()).hexdigest()
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.json")
        
        try:
            # Convert to dict for JSON serialization
            article_dict = {
                "url": article.url,
                "title": article.title,
                "content": article.content,
                "author": article.author,
                "publish_date": article.publish_date,
                "category": article.category,
                "tags": article.tags,
                "summary": article.summary,
                "image_url": article.image_url,
                "images": article.images,
                "extraction_method": article.extraction_method,
                "extraction_time": article.extraction_time,
                "content_length": article.content_length,
                "word_count": article.word_count,
                "links_count": article.links_count,
                "metadata": article.metadata
            }
            
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(article_dict, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            self.logger.debug(f"Cache write error for {article.url}: {e}")
    
    def _get_stats_summary(self) -> Dict[str, Any]:
        """Get extraction statistics summary."""
        total = self.stats["total_extracted"]
        
        if total == 0:
            return self.stats
        
        return {
            **self.stats,
            "json_css_rate": self.stats["json_css_success"] / total,
            "llm_rate": self.stats["llm_success"] / total if self.enable_llm else 0,
            "fallback_rate": self.stats["fallback_success"] / total,
            "cache_hit_rate": self.stats["cache_hits"] / total if self.stats.get("cache_hits") else 0,
            "avg_time": self.stats["total_time"] / total
        }
    
    async def clear_cache(self, max_age_hours: int = 24):
        """Clear old cache files."""
        try:
            cache_files = os.listdir(self.cache_dir)
            cleared = 0
            
            for filename in cache_files:
                if filename.endswith('.json'):
                    filepath = os.path.join(self.cache_dir, filename)
                    if time.time() - os.path.getmtime(filepath) > max_age_hours * 3600:
                        os.remove(filepath)
                        cleared += 1
            
            self.logger.info(f"Cleared {cleared} old cache files")
            
        except Exception as e:
            self.logger.error(f"Error clearing cache: {e}")


# Example usage and testing
async def main():
    """Example usage of the advanced extractor."""
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Initialize extractor
    extractor = AdvancedCrawl4AIExtractor(
        enable_llm=False  # Set to True and provide API key for LLM support
    )
    
    # Test URLs
    test_urls = [
        "https://vnexpress.net/the-gioi",
        "https://dantri.com.vn",
        "https://tuoitre.vn"
    ]
    
    # Extract content
    result = await extractor.extract_urls(test_urls)
    
    # Display results
    print(f"\n=� Extraction Results:")
    print(f"Total URLs: {result.total_urls}")
    print(f"Successful: {result.successful}")
    print(f"Failed: {result.failed}")
    print(f"Execution time: {result.execution_time:.2f}s")
    
    print(f"\n=� Statistics:")
    for key, value in result.stats.items():
        print(f"  {key}: {value}")
    
    print(f"\n=� Extracted Articles:")
    for article in result.articles:
        print(f"\n  URL: {article.url}")
        print(f"  Title: {article.title[:100]}")
        print(f"  Content: {article.content[:200]}...")
        print(f"  Author: {article.author}")
        print(f"  Date: {article.publish_date}")
        print(f"  Method: {article.extraction_method}")
        print(f"  Images: {len(article.images)}")
        print(f"  Word count: {article.word_count}")


if __name__ == "__main__":
    asyncio.run(main())