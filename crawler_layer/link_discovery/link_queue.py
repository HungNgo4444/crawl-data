"""
Crawl queue management with priority and rate limiting
"""

import asyncio
import heapq
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field  
from datetime import datetime, timedelta
import logging
from .rss_crawler import ArticleLink

logger = logging.getLogger(__name__)

@dataclass
class QueuedLink:
    """Link with queue metadata"""
    link: ArticleLink
    priority: float
    added_at: datetime = field(default_factory=datetime.now)
    retry_count: int = 0
    max_retries: int = 3
    
    def __lt__(self, other):
        # Higher priority first (reverse order for min-heap)
        return self.priority > other.priority

class LinkQueue:
    """High-performance priority queue for crawl links"""
    
    def __init__(self, max_size: int = 10000):
        self.max_size = max_size
        self._queue: List[QueuedLink] = []
        self._seen_hashes: set = set()
        self._in_progress: Dict[str, datetime] = {}
        self._failed_links: List[QueuedLink] = []
        self._stats = {
            'total_added': 0,
            'total_processed': 0,
            'total_failed': 0,
            'duplicates_skipped': 0
        }
        
    async def add_links(self, links: List[ArticleLink]):
        """Add multiple links to the queue with deduplication"""
        added_count = 0
        
        for link in links:
            if link.url_hash not in self._seen_hashes:
                if len(self._queue) < self.max_size:
                    queued_link = QueuedLink(
                        link=link,
                        priority=link.priority_score
                    )
                    heapq.heappush(self._queue, queued_link)
                    self._seen_hashes.add(link.url_hash)
                    added_count += 1
                    self._stats['total_added'] += 1
                else:
                    logger.warning("Queue is full, dropping lower priority links")
                    break
            else:
                self._stats['duplicates_skipped'] += 1
        
        logger.info(f"Added {added_count} new links to queue. Queue size: {len(self._queue)}")
    
    async def get_next_batch(self, batch_size: int = 10) -> List[ArticleLink]:
        """Get next batch of links to crawl"""
        batch = []
        
        while len(batch) < batch_size and self._queue:
            queued_link = heapq.heappop(self._queue)
            
            # Mark as in progress
            self._in_progress[queued_link.link.url_hash] = datetime.now()
            batch.append(queued_link.link)
        
        if batch:
            logger.info(f"Retrieved batch of {len(batch)} links for crawling")
        
        return batch
    
    async def mark_completed(self, url_hash: str, success: bool = True):
        """Mark a link as completed (success or failure)"""
        if url_hash in self._in_progress:
            del self._in_progress[url_hash]
            
            if success:
                self._stats['total_processed'] += 1
            else:
                self._stats['total_failed'] += 1
                # TODO: Implement retry logic for failed links
        
    async def mark_failed(self, url_hash: str, retry: bool = True):
        """Mark a link as failed and optionally retry"""
        await self.mark_completed(url_hash, success=False)
        
        if retry:
            # Find the failed link in progress and add back to queue
            # This is a simplified version - in production you'd want more sophisticated retry logic
            pass
    
    def get_queue_size(self) -> int:
        """Get current queue size"""
        return len(self._queue)
    
    def get_in_progress_count(self) -> int:
        """Get number of links currently being processed"""
        return len(self._in_progress)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get queue statistics"""
        return {
            **self._stats,
            'queue_size': len(self._queue),
            'in_progress': len(self._in_progress),
            'failed_count': len(self._failed_links)
        }
    
    def get_top_links(self, count: int = 10) -> List[Dict[str, Any]]:
        """Get top priority links without removing them from queue"""
        top_links = []
        temp_queue = self._queue.copy()
        
        for _ in range(min(count, len(temp_queue))):
            if temp_queue:
                queued_link = heapq.heappop(temp_queue)
                top_links.append({
                    'url': queued_link.link.url,
                    'title': queued_link.link.title,
                    'source': queued_link.link.source,
                    'priority': queued_link.priority,
                    'published_at': queued_link.link.published_at
                })
        
        return top_links
    
    async def cleanup_stale_progress(self, timeout_minutes: int = 30):
        """Remove stale in-progress items"""
        cutoff_time = datetime.now() - timedelta(minutes=timeout_minutes)
        stale_hashes = [
            url_hash for url_hash, start_time in self._in_progress.items()
            if start_time < cutoff_time
        ]
        
        for url_hash in stale_hashes:
            del self._in_progress[url_hash]
            logger.warning(f"Removed stale in-progress item: {url_hash}")
        
        if stale_hashes:
            logger.info(f"Cleaned up {len(stale_hashes)} stale in-progress items")
    
    def clear_queue(self):
        """Clear all items from queue"""
        self._queue.clear()
        self._seen_hashes.clear()
        self._in_progress.clear()
        logger.info("Queue cleared")