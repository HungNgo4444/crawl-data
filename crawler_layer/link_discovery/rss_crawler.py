"""
Ultra-fast RSS feed crawler for link discovery
Target: 1000+ links trong <30 seconds
"""

import asyncio
import aiohttp
import feedparser
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import logging

logger = logging.getLogger(__name__)

@dataclass
class ArticleLink:
    """Lightweight article link data structure"""
    url: str
    title: str
    published_at: Optional[datetime]
    source: str
    description: Optional[str] = None
    priority_score: float = 0.0
    url_hash: str = None
    
    def __post_init__(self):
        if self.url_hash is None:
            self.url_hash = hashlib.md5(self.url.encode()).hexdigest()

class RSSCrawler:
    """Ultra-fast RSS feed crawler for link discovery"""
    
    def __init__(self, timeout: int = 10, max_concurrent: int = 20):
        self.timeout = timeout
        self.max_concurrent = max_concurrent
        
    async def crawl_feeds(self, sources: List[Dict[str, Any]]) -> List[ArticleLink]:
        """
        Crawl multiple RSS feeds concurrently
        Target: 1000+ links trong <30 seconds
        """
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout),
            headers={'User-Agent': 'Mozilla/5.0 (compatible; NewsBot/1.0)'}
        ) as session:
            tasks = [
                self._crawl_single_feed(session, semaphore, source) 
                for source in sources
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results and flatten
        all_links = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"RSS crawl error: {result}")
                continue
            if isinstance(result, list):
                all_links.extend(result)
        
        logger.info(f"Collected {len(all_links)} links from {len(sources)} RSS feeds")
        return all_links
    
    async def _crawl_single_feed(
        self, 
        session: aiohttp.ClientSession, 
        semaphore: asyncio.Semaphore,
        source_config: Dict[str, Any]
    ) -> List[ArticleLink]:
        """Crawl a single RSS feed"""
        async with semaphore:
            try:
                source_name = source_config.get('name', 'unknown')
                rss_urls = source_config.get('rss_feeds', [])
                
                if not rss_urls:
                    return []
                
                # Crawl all RSS URLs for this source
                feed_tasks = [
                    self._fetch_and_parse_feed(session, url, source_name)
                    for url in rss_urls
                ]
                feed_results = await asyncio.gather(*feed_tasks, return_exceptions=True)
                
                # Flatten results
                links = []
                for result in feed_results:
                    if isinstance(result, list):
                        links.extend(result)
                
                return links
                
            except Exception as e:
                logger.error(f"Error crawling source {source_config.get('name')}: {e}")
                return []
    
    async def _fetch_and_parse_feed(
        self, 
        session: aiohttp.ClientSession,
        rss_url: str,
        source_name: str
    ) -> List[ArticleLink]:
        """Fetch and parse a single RSS feed"""
        try:
            async with session.get(rss_url) as response:
                if response.status != 200:
                    logger.warning(f"RSS feed {rss_url} returned status {response.status}")
                    return []
                
                content = await response.text()
                
            # Parse RSS feed
            feed = feedparser.parse(content)
            
            links = []
            for entry in feed.entries:
                try:
                    # Extract published date
                    published_at = None
                    if hasattr(entry, 'published_parsed') and entry.published_parsed:
                        published_at = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                    elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                        published_at = datetime(*entry.updated_parsed[:6], tzinfo=timezone.utc)
                    
                    # Create article link
                    link = ArticleLink(
                        url=entry.link,
                        title=entry.title,
                        published_at=published_at,
                        source=source_name,
                        description=getattr(entry, 'summary', None),
                        priority_score=self._calculate_priority_score(entry, published_at)
                    )
                    
                    links.append(link)
                    
                except Exception as e:
                    logger.warning(f"Error parsing RSS entry from {rss_url}: {e}")
                    continue
            
            logger.debug(f"Parsed {len(links)} links from {rss_url}")
            return links
            
        except Exception as e:
            logger.error(f"Error fetching RSS feed {rss_url}: {e}")
            return []
    
    def _calculate_priority_score(self, entry, published_at: Optional[datetime]) -> float:
        """Calculate priority score for an article link"""
        score = 0.0
        
        # Recency score (newer articles get higher score)
        if published_at:
            age_hours = (datetime.now(timezone.utc) - published_at).total_seconds() / 3600
            if age_hours < 1:
                score += 10.0  # Very fresh
            elif age_hours < 6:
                score += 8.0   # Fresh
            elif age_hours < 24:
                score += 5.0   # Recent
            elif age_hours < 72:
                score += 2.0   # Somewhat recent
        
        # Title quality score
        title = getattr(entry, 'title', '').lower()
        
        # Financial keywords get higher priority
        financial_keywords = ['chứng khoán', 'đầu tư', 'tài chính', 'ngân hàng', 'vàng', 'bất động sản']
        for keyword in financial_keywords:
            if keyword in title:
                score += 3.0
                break
        
        # Business keywords
        business_keywords = ['kinh doanh', 'doanh nghiệp', 'công ty', 'thị trường']
        for keyword in business_keywords:
            if keyword in title:
                score += 2.0
                break
        
        return score