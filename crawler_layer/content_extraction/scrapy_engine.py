"""
Ultra-fast Scrapy engine for static content
Target: 50-100 articles per minute
"""

import asyncio
import aiohttp
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import logging
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin, urlparse
import hashlib

logger = logging.getLogger(__name__)

@dataclass
class ExtractedArticle:
    """Extracted article data"""
    url: str
    url_hash: str
    title: str
    content: str
    author: Optional[str] = None
    published_at: Optional[datetime] = None
    description: Optional[str] = None
    source: str = None
    raw_html: str = None
    word_count: int = 0
    reading_time: int = 0
    language: str = 'vi'
    quality_score: float = 0.0
    extracted_at: datetime = None
    
    def __post_init__(self):
        if self.url_hash is None:
            self.url_hash = hashlib.md5(self.url.encode()).hexdigest()
        if self.extracted_at is None:
            self.extracted_at = datetime.now()
        if self.word_count == 0 and self.content:
            self.word_count = len(self.content.split())
            self.reading_time = max(1, self.word_count // 200)  # ~200 words per minute

class ScrapyEngine:
    """Ultra-fast Scrapy engine for static content"""
    
    def __init__(self, timeout: int = 15, max_concurrent: int = 10):
        self.timeout = timeout
        self.max_concurrent = max_concurrent
        self.session_config = {
            'timeout': aiohttp.ClientTimeout(total=timeout),
            'headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'vi-VN,vi;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
        }
    
    async def crawl_batch(self, crawl_configs: List[Dict[str, Any]]) -> List[ExtractedArticle]:
        """
        Batch crawl multiple URLs concurrently
        Target: 50-100 articles per minute
        """
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        async with aiohttp.ClientSession(**self.session_config) as session:
            tasks = [
                self._crawl_single_article(session, semaphore, config)
                for config in crawl_configs
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        articles = []
        errors = 0
        
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Crawl error: {result}")
                errors += 1
            elif isinstance(result, ExtractedArticle):
                articles.append(result)
        
        logger.info(f"Scrapy engine processed {len(articles)} articles, {errors} errors")
        return articles
    
    async def _crawl_single_article(
        self,
        session: aiohttp.ClientSession,
        semaphore: asyncio.Semaphore,
        config: Dict[str, Any]
    ) -> Optional[ExtractedArticle]:
        """Crawl a single article"""
        async with semaphore:
            try:
                url = config['url']
                site_profile = config.get('site_profile')
                selectors = config.get('selectors', {})
                
                # Add custom headers if specified
                headers = {}
                if site_profile and site_profile.custom_headers:
                    headers.update(site_profile.custom_headers)
                
                # Fetch page content
                async with session.get(url, headers=headers) as response:
                    if response.status != 200:
                        logger.warning(f"HTTP {response.status} for {url}")
                        return None
                    
                    html_content = await response.text()
                
                # Parse with BeautifulSoup
                soup = BeautifulSoup(html_content, 'html.parser')
                
                # Extract article data
                article = await self._extract_article_data(
                    url, soup, html_content, selectors, site_profile
                )
                
                if article and self._is_valid_article(article):
                    return article
                else:
                    logger.debug(f"Invalid article extracted from {url}")
                    return None
                
            except asyncio.TimeoutError:
                logger.warning(f"Timeout crawling {config.get('url')}")
                return None
            except Exception as e:
                logger.error(f"Error crawling {config.get('url')}: {e}")
                return None
    
    async def _extract_article_data(
        self,
        url: str,
        soup: BeautifulSoup,
        raw_html: str,
        selectors: Dict[str, str],
        site_profile: Any
    ) -> Optional[ExtractedArticle]:
        """Extract article data using CSS selectors"""
        
        try:
            # Extract title
            title = self._extract_text_by_selectors(soup, selectors.get('title', 'h1'))
            if not title:
                logger.debug(f"No title found for {url}")
                return None
            
            # Extract main content
            content = self._extract_content_by_selectors(soup, selectors.get('content', '.content'))
            if not content or len(content.strip()) < 100:
                logger.debug(f"Insufficient content for {url}")
                return None
            
            # Extract optional fields
            author = self._extract_text_by_selectors(soup, selectors.get('author', '.author'))
            description = self._extract_text_by_selectors(soup, selectors.get('description', '.description'))
            
            # Extract publish time
            published_at = self._extract_publish_time(soup, selectors.get('publish_time', '.date'))
            
            # Create article object
            article = ExtractedArticle(
                url=url,
                title=title.strip(),
                content=content.strip(),
                author=author.strip() if author else None,
                published_at=published_at,
                description=description.strip() if description else None,
                source=site_profile.name if site_profile else self._extract_domain(url),
                raw_html=raw_html
            )
            
            # Calculate quality score
            article.quality_score = self._calculate_quality_score(article)
            
            return article
            
        except Exception as e:
            logger.error(f"Error extracting article data from {url}: {e}")
            return None
    
    def _extract_text_by_selectors(self, soup: BeautifulSoup, selector: str) -> Optional[str]:
        """Extract text using CSS selector with fallbacks"""
        if not selector:
            return None
        
        # Split multiple selectors by comma
        selectors = [s.strip() for s in selector.split(',')]
        
        for sel in selectors:
            try:
                element = soup.select_one(sel)
                if element:
                    return element.get_text(strip=True)
            except Exception as e:
                logger.debug(f"Selector '{sel}' failed: {e}")
                continue
        
        return None
    
    def _extract_content_by_selectors(self, soup: BeautifulSoup, selector: str) -> Optional[str]:
        """Extract main content with cleaning"""
        content_text = self._extract_text_by_selectors(soup, selector)
        
        if not content_text:
            # Fallback content extraction
            content_text = self._fallback_content_extraction(soup)
        
        if content_text:
            # Clean content
            content_text = self._clean_content(content_text)
        
        return content_text
    
    def _fallback_content_extraction(self, soup: BeautifulSoup) -> Optional[str]:
        """Fallback content extraction when selectors fail"""
        
        # Try common content selectors
        fallback_selectors = [
            '.article-content',
            '.post-content', 
            '.entry-content',
            '[class*="content"]',
            'article',
            '.main-content'
        ]
        
        for selector in fallback_selectors:
            try:
                element = soup.select_one(selector)
                if element:
                    text = element.get_text(separator=' ', strip=True)
                    if len(text) > 200:  # Minimum content length
                        return text
            except:
                continue
        
        # Last resort: extract from paragraphs
        paragraphs = soup.find_all('p')
        if paragraphs:
            content_parts = []
            for p in paragraphs:
                text = p.get_text(strip=True)
                if len(text) > 20:  # Skip very short paragraphs
                    content_parts.append(text)
            
            if content_parts:
                return ' '.join(content_parts)
        
        return None
    
    def _clean_content(self, content: str) -> str:
        """Clean extracted content"""
        if not content:
            return content
        
        # Remove extra whitespace
        content = re.sub(r'\s+', ' ', content)
        
        # Remove common junk patterns
        junk_patterns = [
            r'Theo .+',
            r'Đăng ký nhận tin .+',
            r'Bình luận .+',
            r'Chia sẻ .+',
            r'Tags:.+',
            r'Từ khóa:.+',
            r'Xem thêm:.+',
        ]
        
        for pattern in junk_patterns:
            content = re.sub(pattern, '', content, flags=re.IGNORECASE)
        
        return content.strip()
    
    def _extract_publish_time(self, soup: BeautifulSoup, selector: str) -> Optional[datetime]:
        """Extract and parse publish time"""
        time_text = self._extract_text_by_selectors(soup, selector)
        
        if not time_text:
            # Try to find time in meta tags
            meta_time = soup.find('meta', {'property': 'article:published_time'})
            if meta_time:
                time_text = meta_time.get('content')
        
        if time_text:
            return self._parse_vietnamese_datetime(time_text)
        
        return None
    
    def _parse_vietnamese_datetime(self, time_text: str) -> Optional[datetime]:
        """Parse Vietnamese datetime formats"""
        # This is simplified - in production you'd want more robust parsing
        try:
            # Common patterns for Vietnamese news sites
            patterns = [
                r'(\d{2})/(\d{2})/(\d{4})',  # DD/MM/YYYY
                r'(\d{4})-(\d{2})-(\d{2})',  # YYYY-MM-DD
            ]
            
            for pattern in patterns:
                match = re.search(pattern, time_text)
                if match:
                    # This is very basic parsing - enhance as needed
                    return datetime.now()  # Placeholder
            
        except Exception as e:
            logger.debug(f"Error parsing datetime '{time_text}': {e}")
        
        return None
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL"""
        try:
            domain = urlparse(url).netloc
            if domain.startswith('www.'):
                domain = domain[4:]
            return domain
        except:
            return 'unknown'
    
    def _is_valid_article(self, article: ExtractedArticle) -> bool:
        """Validate extracted article"""
        if not article.title or len(article.title) < 10:
            return False
        
        if not article.content or len(article.content) < 100:
            return False
        
        if article.word_count < 50:
            return False
        
        return True
    
    def _calculate_quality_score(self, article: ExtractedArticle) -> float:
        """Calculate article quality score"""
        score = 0.0
        
        # Length scoring
        if article.word_count > 500:
            score += 3.0
        elif article.word_count > 200:
            score += 2.0
        elif article.word_count > 100:
            score += 1.0
        
        # Title quality
        if len(article.title) > 20 and len(article.title) < 100:
            score += 2.0
        
        # Author presence
        if article.author:
            score += 1.0
        
        # Description presence  
        if article.description:
            score += 1.0
        
        # Published time presence
        if article.published_at:
            score += 1.0
        
        return min(score, 10.0)  # Cap at 10.0