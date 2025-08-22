"""Core Newspaper4k extraction implementation"""

import sys
import os
import time
import requests
from datetime import datetime
from typing import List, Dict, Optional
from urllib.parse import urljoin

# Add newspaper4k to path
newspaper4k_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'newspaper4k-master'))
if newspaper4k_path not in sys.path:
    sys.path.insert(0, newspaper4k_path)

from newspaper import Article, Config
from newspaper.exceptions import ArticleException

from ..models.article_model import Article as ArticleModel, ArticleMetadata, ExtractionResult, ExtractionError
from ..utils.vietnamese_utils import VietnameseTextProcessor
from ..utils.url_utils import URLUtils
from ..config.settings import get_settings


class Newspaper4kExtractor:
    """Core newspaper4k extractor for Vietnamese content"""
    
    def __init__(self):
        self.settings = get_settings()
        self.config = Config()
        self.config.browser_user_agent = self.settings.user_agent
        self.config.request_timeout = self.settings.request_timeout
        self.config.number_threads = 1  # Single thread for simplicity
        
        # Vietnamese language configuration
        self.config.use_meta_language = True
        
    def extract_article(self, url: str) -> Optional[ArticleModel]:
        """Extract single article from URL"""
        try:
            article = Article(url, config=self.config)
            article.download()
            article.parse()
            
            # Extract basic data
            title = VietnameseTextProcessor.normalize_text(article.title or "")
            content = VietnameseTextProcessor.clean_content(article.text or "")
            
            # Skip if no title or content
            if not title or not content or len(content) < self.settings.min_content_length:
                return None
            
            # Extract authors
            authors = []
            if article.authors:
                authors = [VietnameseTextProcessor.normalize_text(author) for author in article.authors]
            
            # Extract publish date
            publish_date = None
            if article.publish_date:
                publish_date = article.publish_date
            elif article.meta_data.get('article:published_time'):
                try:
                    publish_date = datetime.fromisoformat(article.meta_data['article:published_time'].replace('Z', '+00:00'))
                except:
                    pass
            
            # Extract image
            image_url = None
            if article.top_image:
                image_url = article.top_image
            
            # Extract video
            video_url = None
            if article.movies:
                video_url = article.movies[0] if article.movies else None
            
            # Extract metadata
            metadata = ArticleMetadata(
                tags=article.tags or [],
                keywords=article.keywords or [],
                description=article.meta_description or "",
                language="vi" if VietnameseTextProcessor.is_vietnamese_content(content) else "unknown",
                word_count=len(content.split())
            )
            
            return ArticleModel(
                url=url,
                title=title,
                author=authors,
                category="",  # Will be filled by processor if available
                content=content,
                url_image=image_url,
                metadata=metadata,
                publish_date=publish_date,
                url_video=video_url,
                extraction_quality=1.0  # Always 1.0 since no quality scoring
            )
            
        except ArticleException as e:
            print(f"Article extraction failed for {url}: {e}")
            return None
        except Exception as e:
            print(f"Unexpected error extracting {url}: {e}")
            return None
    
    def extract_articles_from_urls(self, urls: List[str], max_articles: int = None) -> ExtractionResult:
        """Extract articles from list of URLs"""
        start_time = time.time()
        articles = []
        errors = []
        
        # Limit URLs if specified
        if max_articles:
            urls = urls[:max_articles]
        
        print(f"Extracting {len(urls)} articles...")
        
        for i, url in enumerate(urls):
            print(f"Processing {i+1}/{len(urls)}: {url}")
            
            try:
                article = self.extract_article(url)
                if article:
                    articles.append(article)
                else:
                    errors.append(ExtractionError(
                        url=url,
                        error="Failed to extract content",
                        error_type="extraction_failed"
                    ))
                    
                # Add delay between requests
                time.sleep(self.settings.request_delay)
                
            except Exception as e:
                errors.append(ExtractionError(
                    url=url,
                    error=str(e),
                    error_type="unexpected_error"
                ))
        
        processing_time = time.time() - start_time
        
        return ExtractionResult(
            domain=URLUtils.extract_domain(urls[0]) if urls else "",
            total_articles=len(urls),
            success_count=len(articles),
            articles=articles,
            errors=errors,
            processing_time=processing_time
        )
    
    def extract_from_domain(self, domain_data: Dict, max_articles: int = None) -> ExtractionResult:
        """Extract articles from domain using available URLs"""
        all_urls = []
        
        # Use example URL if available
        if domain_data.get('url_example'):
            all_urls.append(domain_data['url_example'])
        
        # Use RSS feeds if available
        if domain_data.get('rss_feeds'):
            for rss_url in domain_data['rss_feeds'][:3]:  # Limit to first 3 RSS feeds
                try:
                    rss_articles = self._extract_from_rss(rss_url)
                    all_urls.extend(rss_articles[:10])  # Limit per feed
                except Exception as e:
                    print(f"RSS extraction failed for {rss_url}: {e}")
        
        # Use sitemap if available
        if domain_data.get('sitemaps') and len(all_urls) < 20:
            for sitemap_url in domain_data['sitemaps'][:2]:  # Limit to first 2 sitemaps
                try:
                    sitemap_articles = self._extract_from_sitemap(sitemap_url)
                    all_urls.extend(sitemap_articles[:10])  # Limit per sitemap
                except Exception as e:
                    print(f"Sitemap extraction failed for {sitemap_url}: {e}")
        
        # Remove duplicates
        all_urls = URLUtils.deduplicate_urls(all_urls)
        
        # Filter for article URLs
        article_urls = [url for url in all_urls if URLUtils.is_article_url(url)]
        
        print(f"Found {len(article_urls)} article URLs for domain {domain_data['name']}")
        
        return self.extract_articles_from_urls(article_urls, max_articles)
    
    def _extract_from_rss(self, rss_url: str) -> List[str]:
        """Extract article URLs from RSS feed"""
        try:
            import feedparser
            feed = feedparser.parse(rss_url)
            
            urls = []
            for entry in feed.entries[:20]:  # Limit to 20 entries
                if hasattr(entry, 'link') and entry.link:
                    urls.append(entry.link)
            
            return urls
        except Exception as e:
            print(f"RSS parsing failed: {e}")
            return []
    
    def _extract_from_sitemap(self, sitemap_url: str) -> List[str]:
        """Extract article URLs from sitemap"""
        try:
            response = requests.get(sitemap_url, timeout=self.settings.request_timeout)
            response.raise_for_status()
            
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.content, 'xml')
            
            urls = []
            # Handle regular sitemap
            for loc in soup.find_all('loc'):
                if loc.text:
                    urls.append(loc.text)
            
            # Limit results
            return urls[:50]
            
        except Exception as e:
            print(f"Sitemap parsing failed: {e}")
            return []
