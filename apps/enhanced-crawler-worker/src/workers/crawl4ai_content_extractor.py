"""
Crawl4AI Content Extractor - Structured data extraction với JsonCssExtractionStrategy integration

This module implements comprehensive content extraction using domain_analyzer generated
CSS selectors với multi-strategy fallback for Vietnamese news domains.

Features:
- JsonCssExtractionStrategy integration với domain-specific CSS selectors
- Multi-strategy fallback: CSS selectors → Generic Crawl4AI → Basic HTML parsing
- Batch processing với concurrency control
- Vietnamese content validation và quality assessment
- Database integration với extraction results tracking
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass
from urllib.parse import urlparse, urljoin

# Import Crawl4AI components
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'crawl4ai-main'))

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from crawl4ai.extraction_strategy import JsonCssExtractionStrategy, LLMExtractionStrategy
from crawl4ai.content_filter_strategy import PruningContentFilter
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
from crawl4ai.async_logger import AsyncLogger

# Basic HTML parsing fallback
from bs4 import BeautifulSoup
import re

@dataclass
class ExtractionResult:
    """Result of content extraction"""
    url: str
    success: bool
    extraction_method: str
    quality_score: float
    
    # Structured data fields
    title: Optional[str] = None
    content: Optional[str] = None
    author: Optional[str] = None
    publish_date: Optional[str] = None
    category: Optional[str] = None
    url_image: Optional[str] = None
    tags: List[str] = None
    summary: Optional[str] = None
    
    # Metadata
    extraction_time: float = 0.0
    error_message: Optional[str] = None
    extraction_metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.extraction_metadata is None:
            self.extraction_metadata = {}

class Crawl4AIContentExtractor:
    """Main content extractor using Crawl4AI with CSS selector integration"""
    
    def __init__(self, browser_config: Optional[BrowserConfig] = None):
        # Use standard logging instead of AsyncLogger for now
        import logging
        self.logger = logging.getLogger("Crawl4AIContentExtractor")
        
        # Default browser configuration
        self.browser_config = browser_config or BrowserConfig(
            headless=True,
            verbose=False
        )
        
        # Vietnamese content patterns for validation
        self.vietnamese_patterns = [
            "tin tức", "báo chí", "thời sự", "phóng viên", "ngày", "tháng", 
            "năm", "hôm nay", "chiều nay", "sáng nay", "theo", "cho biết", 
            "thông tin", "việt nam", "đã", "đang", "sẽ", "từ", "tại", "với"
        ]
        
    async def extract_content_batch(
        self, 
        urls: List[Dict[str, Any]], 
        domain_config: Dict[str, Any],
        batch_size: int = 10,
        max_concurrent: int = 5
    ) -> Dict[str, Any]:
        """Extract content from URLs in batches với concurrency control"""
        
        start_time = time.time()
        results = []
        successful_count = 0
        failed_count = 0
        
        # Process URLs in batches
        for i in range(0, len(urls), batch_size):
            batch = urls[i:i+batch_size]
            
            # Create semaphore for concurrency control
            semaphore = asyncio.Semaphore(max_concurrent)
            
            async def extract_single_with_semaphore(url_data):
                async with semaphore:
                    return await self.extract_single_content(
                        url_data['url'], 
                        domain_config
                    )
            
            # Process batch concurrently
            batch_tasks = [extract_single_with_semaphore(url_data) for url_data in batch]
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            # Process results
            for result in batch_results:
                if isinstance(result, Exception):
                    failed_count += 1
                    self.logger.error(f"Batch extraction error: {result}")
                else:
                    results.append(result)
                    if result.success:
                        successful_count += 1
                    else:
                        failed_count += 1
            
            self.logger.info(f"Processed batch {i//batch_size + 1}: {len(batch)} URLs")
        
        total_time = time.time() - start_time
        
        return {
            'total_processed': len(urls),
            'successful_count': successful_count,
            'failed_count': failed_count,
            'total_time': total_time,
            'results': results,
            'avg_time_per_url': total_time / len(urls) if urls else 0
        }
    
    async def extract_single_content(
        self, 
        url: str, 
        domain_config: Dict[str, Any],
        css_selectors: Optional[Dict[str, Any]] = None
    ) -> ExtractionResult:
        """Extract content from single URL với multi-strategy fallback"""
        
        start_time = time.time()
        extraction_attempts = []
        
        try:
            # Strategy 1: CSS Selectors (if provided)
            if css_selectors:
                try:
                    result = await self._extract_with_css_selectors(url, css_selectors)
                    if self._validate_extraction_quality(result):
                        result.extraction_time = time.time() - start_time
                        extraction_attempts.append({
                            "method": "css_selectors",
                            "success": True,
                            "quality_score": result.quality_score
                        })
                        result.extraction_metadata["extraction_attempts"] = extraction_attempts
                        return result
                    else:
                        extraction_attempts.append({
                            "method": "css_selectors",
                            "success": False,
                            "reason": "low_quality_score"
                        })
                except Exception as e:
                    extraction_attempts.append({
                        "method": "css_selectors",
                        "success": False,
                        "error": str(e)
                    })
                    self.logger.warning(f"CSS selector extraction failed for {url}: {e}")
            
            # Strategy 2: Generic Crawl4AI extraction
            try:
                result = await self._extract_with_generic_crawl4ai(url, domain_config)
                if self._validate_extraction_quality(result):
                    result.extraction_time = time.time() - start_time
                    extraction_attempts.append({
                        "method": "generic_crawl4ai",
                        "success": True,
                        "quality_score": result.quality_score
                    })
                    result.extraction_metadata["extraction_attempts"] = extraction_attempts
                    return result
                else:
                    extraction_attempts.append({
                        "method": "generic_crawl4ai", 
                        "success": False,
                        "reason": "insufficient_quality"
                    })
            except Exception as e:
                extraction_attempts.append({
                    "method": "generic_crawl4ai",
                    "success": False,
                    "error": str(e)
                })
                self.logger.warning(f"Generic Crawl4AI extraction failed for {url}: {e}")
            
            # Strategy 3: Basic HTML parsing fallback
            result = await self._extract_with_basic_parsing(url)
            extraction_attempts.append({
                "method": "basic_html_parsing",
                "success": True,
                "quality_score": result.quality_score
            })
            
            result.extraction_time = time.time() - start_time
            result.extraction_metadata["extraction_attempts"] = extraction_attempts
            return result
            
        except Exception as e:
            # Complete failure
            return ExtractionResult(
                url=url,
                success=False,
                extraction_method="failed",
                quality_score=0.0,
                extraction_time=time.time() - start_time,
                error_message=str(e),
                extraction_metadata={"extraction_attempts": extraction_attempts}
            )
    
    async def _extract_with_css_selectors(
        self, 
        url: str, 
        css_schema: Dict[str, Any]
    ) -> ExtractionResult:
        """Extract using JsonCssExtractionStrategy với domain selectors"""
        
        # Initialize extraction strategy
        extraction_strategy = JsonCssExtractionStrategy(schema=css_schema)
        
        async with AsyncWebCrawler(config=self.browser_config) as crawler:
            config = CrawlerRunConfig(
                cache_mode=CacheMode.BYPASS,
                extraction_strategy=extraction_strategy,
                markdown_generator=DefaultMarkdownGenerator(
                    content_filter=PruningContentFilter()
                )
            )
            
            result = await crawler.arun(url=url, config=config)
            
            if result.success and result.extracted_content:
                try:
                    extracted_data = json.loads(result.extracted_content)
                    
                    # Handle both list and single object responses
                    if isinstance(extracted_data, list) and extracted_data:
                        article_data = extracted_data[0]
                    elif isinstance(extracted_data, dict):
                        article_data = extracted_data
                    else:
                        raise ValueError("Invalid extraction data format")
                    
                    return ExtractionResult(
                        url=url,
                        success=True,
                        extraction_method="css_selectors",
                        quality_score=self._calculate_quality_score(article_data),
                        title=article_data.get('title', ''),
                        content=article_data.get('content', ''),
                        author=article_data.get('author', ''),
                        publish_date=article_data.get('publish_date', ''),
                        category=article_data.get('category', ''),
                        url_image=article_data.get('url_image', ''),
                        tags=article_data.get('tags', []),
                        summary=article_data.get('summary', ''),
                        extraction_metadata={
                            "css_schema_used": css_schema,
                            "crawl_result_success": result.success,
                            "extraction_timestamp": datetime.now().isoformat()
                        }
                    )
                except (json.JSONDecodeError, KeyError, ValueError) as e:
                    raise Exception(f"Failed to parse CSS extraction results: {e}")
            else:
                raise Exception(f"CSS extraction failed: {result.error_message if hasattr(result, 'error_message') else 'Unknown error'}")
    
    async def _extract_with_generic_crawl4ai(
        self, 
        url: str, 
        domain_config: Dict[str, Any]
    ) -> ExtractionResult:
        """Extract using generic Crawl4AI với Vietnamese optimization"""
        
        async with AsyncWebCrawler(config=self.browser_config) as crawler:
            config = CrawlerRunConfig(
                cache_mode=CacheMode.BYPASS,
                markdown_generator=DefaultMarkdownGenerator(
                    content_filter=PruningContentFilter()
                )
            )
            
            result = await crawler.arun(url=url, config=config)
            
            if result.success:
                # Parse content using markdown and HTML
                content = result.markdown.raw_markdown if result.markdown else ""
                html_content = result.cleaned_html if hasattr(result, 'cleaned_html') else ""
                
                # Extract basic fields using heuristics
                extracted_data = self._extract_basic_fields_from_content(content, html_content, url)
                
                return ExtractionResult(
                    url=url,
                    success=True,
                    extraction_method="generic_crawl4ai",
                    quality_score=self._calculate_quality_score(extracted_data),
                    title=extracted_data.get('title', ''),
                    content=extracted_data.get('content', ''),
                    author=extracted_data.get('author', ''),
                    publish_date=extracted_data.get('publish_date', ''),
                    category=extracted_data.get('category', ''),
                    url_image=extracted_data.get('url_image', ''),
                    tags=extracted_data.get('tags', []),
                    summary=extracted_data.get('summary', ''),
                    extraction_metadata={
                        "method": "generic_crawl4ai",
                        "content_length": len(content),
                        "html_length": len(html_content),
                        "extraction_timestamp": datetime.now().isoformat()
                    }
                )
            else:
                raise Exception(f"Generic Crawl4AI failed: {result.error_message if hasattr(result, 'error_message') else 'Unknown error'}")
    
    async def _extract_with_basic_parsing(self, url: str) -> ExtractionResult:
        """Basic HTML parsing fallback method"""
        
        import httpx
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Basic field extraction using common patterns
            extracted_data = {
                'title': self._extract_title_basic(soup),
                'content': self._extract_content_basic(soup),
                'author': self._extract_author_basic(soup),
                'publish_date': self._extract_date_basic(soup),
                'category': self._extract_category_basic(soup),
                'url_image': self._extract_image_basic(soup, url),
                'tags': [],
                'summary': ''
            }
            
            return ExtractionResult(
                url=url,
                success=True,
                extraction_method="basic_html_parsing",
                quality_score=self._calculate_quality_score(extracted_data),
                title=extracted_data.get('title', ''),
                content=extracted_data.get('content', ''),
                author=extracted_data.get('author', ''),
                publish_date=extracted_data.get('publish_date', ''),
                category=extracted_data.get('category', ''),
                url_image=extracted_data.get('url_image', ''),
                tags=extracted_data.get('tags', []),
                summary=extracted_data.get('summary', ''),
                extraction_metadata={
                    "method": "basic_html_parsing",
                    "extraction_timestamp": datetime.now().isoformat()
                }
            )
    
    def _extract_basic_fields_from_content(
        self, 
        markdown_content: str, 
        html_content: str, 
        url: str
    ) -> Dict[str, Any]:
        """Extract basic fields from markdown and HTML content"""
        
        # Parse HTML for structured extraction
        soup = BeautifulSoup(html_content, 'html.parser') if html_content else None
        
        result = {
            'title': '',
            'content': markdown_content,
            'author': '',
            'publish_date': '',
            'category': '',
            'url_image': '',
            'tags': [],
            'summary': ''
        }
        
        if soup:
            result['title'] = self._extract_title_basic(soup)
            result['author'] = self._extract_author_basic(soup)
            result['publish_date'] = self._extract_date_basic(soup)
            result['category'] = self._extract_category_basic(soup)
            result['url_image'] = self._extract_image_basic(soup, url)
        
        # Generate summary from content
        if markdown_content:
            sentences = re.split(r'[.!?]+', markdown_content)
            result['summary'] = '. '.join(sentences[:3]).strip()
        
        return result
    
    def _extract_title_basic(self, soup: BeautifulSoup) -> str:
        """Extract title using basic patterns"""
        selectors = ['h1', 'title', '.title', '.headline', '.post-title']
        for selector in selectors:
            element = soup.select_one(selector)
            if element and element.get_text().strip():
                return element.get_text().strip()
        return ""
    
    def _extract_content_basic(self, soup: BeautifulSoup) -> str:
        """Extract content using basic patterns"""
        selectors = ['.content', '.article-content', '.post-content', 'article', 'main']
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                text = element.get_text().strip()
                if len(text) > 200:  # Minimum content length
                    return text
        return ""
    
    def _extract_author_basic(self, soup: BeautifulSoup) -> str:
        """Extract author using basic patterns"""
        selectors = ['.author', '.byline', '.writer', '[rel="author"]']
        for selector in selectors:
            element = soup.select_one(selector)
            if element and element.get_text().strip():
                return element.get_text().strip()
        return ""
    
    def _extract_date_basic(self, soup: BeautifulSoup) -> str:
        """Extract publish date using basic patterns"""
        selectors = ['time', '.date', '.published', '.timestamp']
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                # Try datetime attribute first
                datetime_attr = element.get('datetime')
                if datetime_attr:
                    return datetime_attr
                # Fall back to text content
                text = element.get_text().strip()
                if text:
                    return text
        return ""
    
    def _extract_category_basic(self, soup: BeautifulSoup) -> str:
        """Extract category using basic patterns"""
        selectors = ['.category', '.section', '.breadcrumb a:last-child']
        for selector in selectors:
            element = soup.select_one(selector)
            if element and element.get_text().strip():
                return element.get_text().strip()
        return ""
    
    def _extract_image_basic(self, soup: BeautifulSoup, base_url: str) -> str:
        """Extract main image using basic patterns"""
        selectors = ['.featured-image img', 'article img', '.content img']
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                src = element.get('src')
                if src:
                    return urljoin(base_url, src)
        return ""
    
    def _calculate_quality_score(self, extracted_data: Dict[str, Any]) -> float:
        """Calculate quality score for extracted content"""
        score = 0.0
        
        # Title scoring (30%)
        title = extracted_data.get('title', '')
        if title and len(title) > 10:
            score += 0.3
        elif title:
            score += 0.15
        
        # Content scoring (40%)
        content = extracted_data.get('content', '')
        if content and len(content) > 500:
            score += 0.4
        elif content and len(content) > 200:
            score += 0.2
        elif content:
            score += 0.1
        
        # Metadata scoring (30%)
        author = extracted_data.get('author', '')
        publish_date = extracted_data.get('publish_date', '')
        category = extracted_data.get('category', '')
        
        if author:
            score += 0.1
        if publish_date:
            score += 0.1
        if category:
            score += 0.1
        
        # Vietnamese content bonus
        if content and self._is_vietnamese_content(content):
            score += 0.1
        
        return min(score, 1.0)  # Cap at 1.0
    
    def _is_vietnamese_content(self, content: str) -> bool:
        """Check if content contains Vietnamese patterns"""
        content_lower = content.lower()
        matches = sum(1 for pattern in self.vietnamese_patterns if pattern in content_lower)
        return matches >= 3 and len(content) >= 200
    
    def _validate_extraction_quality(self, result: ExtractionResult) -> bool:
        """Validate if extraction meets quality standards"""
        return (
            result.success and 
            result.quality_score >= 0.6 and 
            result.title and 
            result.content and 
            len(result.content) >= 200
        )

# Export main class
__all__ = ['Crawl4AIContentExtractor', 'ExtractionResult']