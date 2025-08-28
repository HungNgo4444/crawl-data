import logging
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from enum import Enum

from ..models.url_models import URLEntry, URLStatus, URLBatch
from ..utils.database import DatabaseManager

logger = logging.getLogger(__name__)


class QueuePriority(int, Enum):
    """Queue priority levels"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


class QueueManager:
    """URL queue management with priority handling"""
    
    def __init__(self, db_manager: DatabaseManager, max_queue_size: int = 10000):
        self.db_manager = db_manager
        self.max_queue_size = max_queue_size
        self._queue_lock = asyncio.Lock()
    
    async def add_urls_to_queue(self, urls: List[str], domain_id: int, 
                               priority: QueuePriority = QueuePriority.NORMAL) -> int:
        """Add URLs to processing queue"""
        try:
            async with self._queue_lock:
                added_count = 0
                
                for url in urls:
                    # Check if URL is already in queue
                    if await self._is_url_in_queue(url, domain_id):
                        logger.debug(f"URL already in queue: {url}")
                        continue
                    
                    # Check queue size limit
                    current_size = await self._get_queue_size(domain_id)
                    if current_size >= self.max_queue_size:
                        logger.warning(f"Queue size limit reached for domain {domain_id}")
                        break
                    
                    # Add to queue
                    success = await self._insert_queue_entry(url, domain_id, priority)
                    if success:
                        added_count += 1
                
                logger.info(f"Added {added_count} URLs to queue for domain {domain_id}")
                return added_count
                
        except Exception as e:
            logger.error(f"Error adding URLs to queue: {e}")
            return 0
    
    async def get_next_batch(self, domain_id: Optional[int] = None, 
                            batch_size: int = 10, 
                            priority_threshold: int = QueuePriority.NORMAL) -> Optional[URLBatch]:
        """Get next batch of URLs to process"""
        try:
            async with self._queue_lock:
                # Build query based on parameters
                where_conditions = ["status = 'pending'"]
                params = []
                
                if domain_id:
                    where_conditions.append("domain_id = %s")
                    params.append(domain_id)
                
                where_conditions.append("priority >= %s")
                params.append(priority_threshold)
                
                where_conditions.append("scheduled_at <= NOW()")
                
                where_clause = " AND ".join(where_conditions)
                
                sql = f"""
                SELECT id, domain_id, url, priority
                FROM monitoring_queue 
                WHERE {where_clause}
                ORDER BY priority DESC, scheduled_at ASC
                LIMIT %s;
                """
                params.append(batch_size)
                
                results = self.db_manager.execute_sql(sql, tuple(params))
                
                if not results:
                    return None
                
                # Extract data
                urls = []
                queue_ids = []
                batch_domain_id = None
                
                for row in results:
                    urls.append(row.get('url'))
                    queue_ids.append(row.get('id'))
                    if batch_domain_id is None:
                        batch_domain_id = int(row.get('domain_id'))
                
                if not urls:
                    return None
                
                # Mark URLs as processing
                await self._mark_urls_processing(queue_ids)
                
                # Create batch
                batch = URLBatch(
                    domain_id=batch_domain_id,
                    urls=urls,
                    priority=max(int(row.get('priority', 1)) for row in results),
                    batch_id=f"batch_{batch_domain_id}_{int(datetime.now().timestamp())}"
                )
                
                logger.info(f"Created batch {batch.batch_id} with {len(urls)} URLs")
                return batch
                
        except Exception as e:
            logger.error(f"Error getting next batch: {e}")
            return None
    
    async def mark_batch_completed(self, batch: URLBatch, success_urls: List[str], 
                                  failed_urls: List[str]) -> bool:
        """Mark batch URLs as completed or failed"""
        try:
            async with self._queue_lock:
                # Mark successful URLs as completed
                if success_urls:
                    await self._update_queue_status(success_urls, batch.domain_id, 'completed')
                
                # Mark failed URLs - increment attempts and possibly retry
                if failed_urls:
                    await self._handle_failed_urls(failed_urls, batch.domain_id)
                
                logger.info(f"Batch {batch.batch_id}: {len(success_urls)} completed, "
                           f"{len(failed_urls)} failed")
                return True
                
        except Exception as e:
            logger.error(f"Error marking batch completed: {e}")
            return False
    
    async def _is_url_in_queue(self, url: str, domain_id: int) -> bool:
        """Check if URL is already in queue"""
        try:
            sql = """
            SELECT COUNT(*) as count
            FROM monitoring_queue 
            WHERE url = %s AND domain_id = %s AND status IN ('pending', 'processing');
            """
            
            results = self.db_manager.execute_sql(sql, (url, domain_id))
            
            if results and len(results) > 0:
                count = int(results[0].get('count', 0))
                return count > 0
            
            return False
            
        except Exception as e:
            logger.debug(f"Error checking URL in queue: {e}")
            return False
    
    async def _get_queue_size(self, domain_id: int) -> int:
        """Get current queue size for domain"""
        try:
            sql = """
            SELECT COUNT(*) as count
            FROM monitoring_queue 
            WHERE domain_id = %s AND status IN ('pending', 'processing');
            """
            
            results = self.db_manager.execute_sql(sql, (domain_id,))
            
            if results and len(results) > 0:
                return int(results[0].get('count', 0))
            
            return 0
            
        except Exception as e:
            logger.error(f"Error getting queue size: {e}")
            return 0
    
    async def _insert_queue_entry(self, url: str, domain_id: int, 
                                 priority: QueuePriority) -> bool:
        """Insert URL into queue"""
        try:
            sql = """
            INSERT INTO monitoring_queue (domain_id, url, priority, scheduled_at, status)
            VALUES (%s, %s, %s, NOW(), 'pending');
            """
            
            result = self.db_manager.execute_sql(sql, (domain_id, url, priority.value))
            return result is not None
            
        except Exception as e:
            logger.error(f"Error inserting queue entry: {e}")
            return False
    
    async def _mark_urls_processing(self, queue_ids: List[int]) -> bool:
        """Mark queue entries as processing"""
        try:
            if not queue_ids:
                return True
            
            ids_str = ','.join(map(str, queue_ids))
            sql = f"""
            UPDATE monitoring_queue 
            SET status = 'processing', attempts = attempts + 1
            WHERE id IN ({ids_str});
            """
            
            result = self.db_manager.execute_sql(sql)
            return result is not None
            
        except Exception as e:
            logger.error(f"Error marking URLs processing: {e}")
            return False
    
    async def _update_queue_status(self, urls: List[str], domain_id: int, status: str) -> bool:
        """Update queue status for URLs"""
        try:
            if not urls:
                return True
            
            # Create placeholders for URLs
            url_placeholders = ','.join(['%s'] * len(urls))
            sql = f"""
            UPDATE monitoring_queue 
            SET status = %s
            WHERE url IN ({url_placeholders}) AND domain_id = %s;
            """
            
            params = [status] + urls + [domain_id]
            result = self.db_manager.execute_sql(sql, tuple(params))
            return result is not None
            
        except Exception as e:
            logger.error(f"Error updating queue status: {e}")
            return False
    
    async def _handle_failed_urls(self, failed_urls: List[str], domain_id: int) -> bool:
        """Handle failed URLs - retry or mark as failed"""
        try:
            max_attempts = 3
            retry_delay_minutes = 60
            
            for url in failed_urls:
                # Get current attempts
                sql = """
                SELECT attempts FROM monitoring_queue 
                WHERE url = %s AND domain_id = %s;
                """
                
                results = self.db_manager.execute_sql(sql, (url, domain_id))
                
                if not results:
                    continue
                
                attempts = int(results[0].get('attempts', 0))
                
                if attempts >= max_attempts:
                    # Max attempts reached, mark as failed
                    update_sql = """
                    UPDATE monitoring_queue 
                    SET status = 'failed'
                    WHERE url = %s AND domain_id = %s;
                    """
                    self.db_manager.execute_sql(update_sql, (url, domain_id))
                else:
                    # Retry later
                    retry_time = datetime.now() + timedelta(minutes=retry_delay_minutes)
                    update_sql = """
                    UPDATE monitoring_queue 
                    SET status = 'pending', scheduled_at = %s
                    WHERE url = %s AND domain_id = %s;
                    """
                    self.db_manager.execute_sql(update_sql, (retry_time.isoformat(), url, domain_id))
            
            return True
            
        except Exception as e:
            logger.error(f"Error handling failed URLs: {e}")
            return False
    
    async def get_queue_statistics(self, domain_id: Optional[int] = None) -> Dict[str, Any]:
        """Get queue statistics"""
        try:
            where_clause = f"WHERE domain_id = {domain_id}" if domain_id else ""
            
            sql = f"""
            SELECT 
                status,
                COUNT(*) as count,
                AVG(attempts) as avg_attempts
            FROM monitoring_queue 
            {where_clause}
            GROUP BY status;
            """
            
            results = self.db_manager.execute_sql(sql)
            
            stats = {
                'pending': 0,
                'processing': 0,
                'completed': 0,
                'failed': 0,
                'total': 0,
                'avg_attempts': 0.0
            }
            
            total_attempts = 0
            total_count = 0
            
            if results:
                for row in results:
                    status = row.get('status', '')
                    count = int(row.get('count', 0))
                    avg_attempts = float(row.get('avg_attempts', 0))
                    
                    if status in stats:
                        stats[status] = count
                        total_attempts += avg_attempts * count
                        total_count += count
            
            stats['total'] = total_count
            stats['avg_attempts'] = total_attempts / total_count if total_count > 0 else 0.0
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting queue statistics: {e}")
            return {'error': str(e)}
    
    async def cleanup_old_queue_entries(self, days_old: int = 7) -> int:
        """Clean up old completed/failed queue entries"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days_old)
            
            sql = """
            DELETE FROM monitoring_queue 
            WHERE status IN ('completed', 'failed') 
            AND created_at < %s;
            """
            
            result = self.db_manager.execute_sql(sql, (cutoff_date.isoformat(),))
            
            if result is not None:
                logger.info(f"Cleaned up old queue entries older than {days_old} days")
                return 1  # Success indicator
            
            return 0
            
        except Exception as e:
            logger.error(f"Error cleaning up queue entries: {e}")
            return 0