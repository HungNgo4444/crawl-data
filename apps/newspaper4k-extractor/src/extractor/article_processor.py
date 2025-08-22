"""Simple article processor using newspaper4k"""

import sys
import os
import time
from datetime import datetime
from typing import List, Dict, Optional


# Add newspaper4k to path
newspaper4k_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'newspaper4k-master'))
if newspaper4k_path not in sys.path:
    sys.path.insert(0, newspaper4k_path)

# Add utils to path
utils_path = os.path.join(os.path.dirname(__file__), '..', 'utils')
if utils_path not in sys.path:
    sys.path.insert(0, utils_path)

import newspaper
import feedparser
from database import DatabaseManager


class ArticleProcessor:
    """Process articles from domains using newspaper4k"""
    
    def __init__(self):
        self.db = DatabaseManager()
    
    def process_domain(self, domain_name: str, max_articles: int = 10) -> Dict:
        """Process articles from a domain"""
        start_time = time.time()
        
        # Get domain data from database
        domain_data = self.db.get_domain_by_name(domain_name)
        if not domain_data:
            return {
                "error": f"Domain {domain_name} not found in database",
                "success": False
            }
        
        print(f"Processing domain: {domain_data['display_name']} ({domain_data['name']})")
        
        articles = []
        errors = []
        
        # Process example URL if available
        if domain_data.get('url_example'):
            print(f"Processing example URL: {domain_data['url_example']}")
            article_data = self._extract_article(domain_data['url_example'])
            if article_data:
                articles.append(article_data)
            else:
                errors.append({
                    "url": domain_data['url_example'],
                    "error": "Failed to extract content"
                })
        
        # Process RSS feeds
        if domain_data.get('rss_feeds') and len(articles) < max_articles:
            for rss_url in domain_data['rss_feeds'][:2]:  # Limit to 2 RSS feeds
                print(f"Processing RSS feed: {rss_url}")
                rss_articles = self._extract_from_rss(rss_url, max_articles - len(articles))
                articles.extend(rss_articles)
                if len(articles) >= max_articles:
                    break
        
        # Process sitemaps if still need more articles
        if domain_data.get('sitemaps') and len(articles) < max_articles:
            for sitemap_url in domain_data['sitemaps'][:2]:  # Limit to 2 sitemaps
                print(f"Processing sitemap: {sitemap_url}")
                sitemap_articles = self._extract_from_sitemap(sitemap_url, max_articles - len(articles))
                articles.extend(sitemap_articles)
                if len(articles) >= max_articles:
                    break
        
        processing_time = time.time() - start_time
        
        result = {
            "domain": domain_data['name'],
            "display_name": domain_data['display_name'],
            "extraction_time": datetime.utcnow().isoformat(),
            "total_articles": len(articles),
            "success_count": len(articles),
            "articles": articles,
            "errors": errors,
            "processing_time": round(processing_time, 2),
            "success": True
        }
        
        return result
    
    def _extract_article(self, url: str) -> Optional[Dict]:
        """Extract single article using newspaper4k"""
        try:
            # Use newspaper4k's simple article function
            art = newspaper.article(url, language='vi')
            
            if not art.title or not art.text or len(art.text.strip()) < 100:
                return None
            
            return {
                "url": url,
                "title": art.title.strip(),
                "author": art.authors or [],
                "category": "",
                "content": art.text.strip(),
                "url_image": art.top_image or "",
                "metadata": {
                    "tags": art.tags or [],
                    "keywords": art.keywords or [],
                    "description": art.meta_description or ""
                },
                "publish_date": art.publish_date.isoformat() if art.publish_date else None,
                "url_video": art.movies[0] if art.movies else ""
            }
            
        except Exception as e:
            print(f"Error extracting article {url}: {e}")
            return None
    
    def _extract_from_rss(self, rss_url: str, max_articles: int) -> List[Dict]:
        """Extract articles from RSS feed"""
        articles = []
        try:
            feed = feedparser.parse(rss_url)
            
            for entry in feed.entries[:max_articles]:
                if hasattr(entry, 'link') and entry.link:
                    article_data = self._extract_article(entry.link)
                    if article_data:
                        articles.append(article_data)
                    
                    # Add delay between requests
                    time.sleep(1)
                    
                    if len(articles) >= max_articles:
                        break
        except Exception as e:
            print(f"RSS processing failed: {e}")
        
        return articles
    
    def _extract_from_sitemap(self, sitemap_url: str, max_articles: int) -> List[Dict]:
        """Extract articles from sitemap - basic implementation"""
        articles = []
        try:
            import requests
            from bs4 import BeautifulSoup
            
            response = requests.get(sitemap_url, timeout=30)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'xml')
                
                urls = []
                for loc in soup.find_all('loc'):
                    if loc.text and 'http' in loc.text:
                        urls.append(loc.text.strip())
                
                # Process first few URLs
                for url in urls[:max_articles]:
                    article_data = self._extract_article(url)
                    if article_data:
                        articles.append(article_data)
                    
                    # Add delay between requests
                    time.sleep(1)
                    
                    if len(articles) >= max_articles:
                        break
                        
        except Exception as e:
            print(f"Sitemap processing failed: {e}")
        
        return articles
    
    def get_all_domains(self) -> List[Dict]:
        """Get all active domains from database"""
        return self.db.get_active_domains()
