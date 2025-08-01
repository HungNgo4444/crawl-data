"""
Smart link filtering and prioritization
"""

import hashlib
from typing import List, Set, Dict, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
import re
from urllib.parse import urlparse
from .rss_crawler import ArticleLink

logger = logging.getLogger(__name__)

class LinkProcessor:
    """Smart link filtering and prioritization"""
    
    def __init__(self):
        self.seen_urls: Set[str] = set()
        self.seen_hashes: Set[str] = set()
        
        # URL patterns to exclude
        self.exclude_patterns = [
            r'/video/',
            r'/photo/',
            r'/gallery/',
            r'\.jpg$',
            r'\.png$',
            r'\.gif$',
            r'\.pdf$',
            r'/tag/',
            r'/tags/',
            r'/author/',
            r'/search',
            r'/login',
            r'/register'
        ]
        
        # Domains to prioritize
        self.priority_domains = {
            'vnexpress.net': 10.0,
            'cafef.vn': 8.0,
            'dantri.com.vn': 8.0,
            'vietnamnet.vn': 7.0,
            'thanhnien.vn': 7.0,
            'tuoitre.vn': 7.0
        }
    
    def filter_and_prioritize(self, raw_links: List[ArticleLink]) -> List[ArticleLink]:
        """
        - Remove duplicates
        - Filter by content type (news, finance)
        - Score by freshness and source reliability
        - Return sorted by priority
        """
        logger.info(f"Processing {len(raw_links)} raw links")
        
        # Step 1: Filter out invalid/unwanted links
        filtered_links = []
        for link in raw_links:
            if self._is_valid_link(link):
                filtered_links.append(link)
        
        logger.info(f"After filtering: {len(filtered_links)} valid links")
        
        # Step 2: Remove duplicates
        unique_links = self._deduplicate_links(filtered_links)
        logger.info(f"After deduplication: {len(unique_links)} unique links")
        
        # Step 3: Calculate final priority scores
        for link in unique_links:
            link.priority_score = self._calculate_final_priority(link)
        
        # Step 4: Sort by priority (highest first)
        sorted_links = sorted(unique_links, key=lambda x: x.priority_score, reverse=True)
        
        logger.info(f"Final processed links: {len(sorted_links)}")
        return sorted_links
    
    def _is_valid_link(self, link: ArticleLink) -> bool:
        """Check if link is valid for crawling"""
        if not link.url or not link.title:
            return False
        
        # Check URL patterns to exclude
        for pattern in self.exclude_patterns:
            if re.search(pattern, link.url, re.IGNORECASE):
                logger.debug(f"Excluded by pattern {pattern}: {link.url}")
                return False
        
        # Check if URL is properly formatted
        try:
            parsed = urlparse(link.url)
            if not parsed.scheme or not parsed.netloc:
                return False
        except Exception:
            return False
        
        # Check title quality
        if len(link.title.strip()) < 10:
            return False
        
        # Exclude social media promotional content
        title_lower = link.title.lower()
        spam_keywords = ['click here', 'xem ngay', 'hot hot', 'khuyến mãi']
        if any(keyword in title_lower for keyword in spam_keywords):
            return False
        
        return True
    
    def _deduplicate_links(self, links: List[ArticleLink]) -> List[ArticleLink]:
        """Remove duplicate links based on URL hash and title similarity"""
        unique_links = []
        seen_hashes = set()
        seen_urls = set()
        
        for link in links:
            # Skip if we've seen this exact URL
            if link.url in seen_urls:
                continue
            
            # Skip if we've seen this URL hash
            if link.url_hash in seen_hashes:
                continue
            
            # Check for similar titles (fuzzy deduplication)
            if self._is_similar_title_exists(link.title, unique_links):
                continue
            
            # Add to unique set
            unique_links.append(link)
            seen_hashes.add(link.url_hash)
            seen_urls.add(link.url)
        
        return unique_links
    
    def _is_similar_title_exists(self, title: str, existing_links: List[ArticleLink]) -> bool:
        """Check if similar title already exists"""
        title_words = set(title.lower().split())
        
        for existing_link in existing_links[-50:]:  # Only check recent links for performance
            existing_words = set(existing_link.title.lower().split())
            
            # Calculate Jaccard similarity
            intersection = title_words.intersection(existing_words)
            union = title_words.union(existing_words)
            
            if len(union) > 0:
                similarity = len(intersection) / len(union)
                if similarity > 0.8:  # 80% similarity threshold
                    return True
        
        return False
    
    def _calculate_final_priority(self, link: ArticleLink) -> float:
        """Calculate final priority score for the link"""
        score = link.priority_score  # Base score from RSS crawler
        
        # Domain authority bonus
        domain = urlparse(link.url).netloc.lower()
        for priority_domain, bonus in self.priority_domains.items():
            if priority_domain in domain:
                score += bonus
                break
        
        # Content category scoring
        title_lower = link.title.lower()
        
        # Financial content gets high priority
        if any(keyword in title_lower for keyword in [
            'chứng khoán', 'cổ phiếu', 'đầu tư', 'tài chính', 'ngân hàng',
            'vàng', 'forex', 'crypto', 'bitcoin', 'bất động sản'
        ]):
            score += 15.0
        
        # Business content gets medium priority  
        elif any(keyword in title_lower for keyword in [
            'kinh doanh', 'doanh nghiệp', 'công ty', 'thị trường',
            'xuất khẩu', 'nhập khẩu', 'gdp', 'lạm phát'
        ]):
            score += 10.0
        
        # Technology and startup content
        elif any(keyword in title_lower for keyword in [
            'công nghệ', 'startup', 'tech', 'ai', 'blockchain'
        ]):
            score += 8.0
        
        # Length bonus (longer articles often more comprehensive)
        if link.description and len(link.description) > 200:
            score += 2.0
        
        # Recency bonus (prefer recent articles)
        if link.published_at:
            hours_old = (datetime.now(link.published_at.tzinfo) - link.published_at).total_seconds() / 3600
            if hours_old < 2:
                score += 5.0
            elif hours_old < 6:
                score += 3.0
            elif hours_old < 24:
                score += 1.0
        
        return score
    
    def get_stats(self) -> Dict[str, Any]:
        """Get processing statistics"""
        return {
            'total_seen_urls': len(self.seen_urls),
            'total_seen_hashes': len(self.seen_hashes)
        }