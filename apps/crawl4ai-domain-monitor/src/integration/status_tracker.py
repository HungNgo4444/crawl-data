import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

from ..models.url_models import ProcessingResult, URLStatus
from ..utils.database import DatabaseManager

logger = logging.getLogger(__name__)


class StatusTracker:
    """Track processing status and statistics"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
    
    async def update_processing_status(self, results: List[ProcessingResult]) -> bool:
        """Update processing status for multiple results"""
        try:
            success_count = 0
            
            for result in results:
                success = await self._update_single_status(result)
                if success:
                    success_count += 1
            
            logger.info(f"Updated status for {success_count}/{len(results)} results")
            return success_count == len(results)
            
        except Exception as e:
            logger.error(f"Error updating processing status: {e}")
            return False
    
    async def _update_single_status(self, result: ProcessingResult) -> bool:
        """Update status for single processing result"""
        try:
            # Determine status based on result
            if result.success:
                status = URLStatus.COMPLETED.value
                error_msg = None
            else:
                status = URLStatus.FAILED.value
                error_msg = result.error
            
            # Update url_tracking table
            sql = """
            UPDATE url_tracking 
            SET status = %s, processed_at = NOW(), last_error = %s,
                processing_attempts = processing_attempts + 1,
                metadata = metadata || %s
            WHERE original_url = %s;
            """
            
            # Prepare metadata
            metadata = {
                'processing_time': result.processing_time,
                'processed_at': datetime.now().isoformat()
            }
            
            if result.extracted_data:
                metadata['extraction_success'] = True
                metadata['content_length'] = len(str(result.extracted_data))
            else:
                metadata['extraction_success'] = False
            
            metadata_json = str(metadata).replace("'", '"')
            
            result_sql = self.db_manager.execute_sql(sql, (
                status, error_msg, metadata_json, result.url
            ))
            
            return result_sql is not None
            
        except Exception as e:
            logger.error(f"Error updating single status for {result.url}: {e}")
            return False
    
    async def get_domain_processing_stats(self, domain_id: int, 
                                        days_back: int = 7) -> Dict[str, Any]:
        """Get processing statistics for domain"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days_back)
            
            sql = """
            SELECT 
                status,
                COUNT(*) as count,
                AVG(processing_attempts) as avg_attempts,
                MIN(created_at) as oldest_entry,
                MAX(processed_at) as latest_processed
            FROM url_tracking 
            WHERE domain_id = %s AND created_at >= %s
            GROUP BY status;
            """
            
            results = self.db_manager.execute_sql(sql, (domain_id, cutoff_date.isoformat()))
            
            stats = {
                'domain_id': domain_id,
                'period_days': days_back,
                'statuses': {},
                'total_urls': 0,
                'success_rate': 0.0,
                'avg_attempts': 0.0,
                'oldest_entry': None,
                'latest_processed': None
            }
            
            if results:
                total_completed = 0
                total_failed = 0
                total_attempts = 0
                total_count = 0
                
                for row in results:
                    status = row.get('status', 'unknown')
                    count = int(row.get('count', 0))
                    avg_attempts = float(row.get('avg_attempts', 0))
                    
                    stats['statuses'][status] = {
                        'count': count,
                        'avg_attempts': avg_attempts
                    }
                    
                    if status == 'completed':
                        total_completed = count
                    elif status == 'failed':
                        total_failed = count
                    
                    total_attempts += avg_attempts * count
                    total_count += count
                    
                    # Track timestamps
                    if row.get('oldest_entry'):
                        if not stats['oldest_entry'] or row.get('oldest_entry') < stats['oldest_entry']:
                            stats['oldest_entry'] = row.get('oldest_entry')
                    
                    if row.get('latest_processed'):
                        if not stats['latest_processed'] or row.get('latest_processed') > stats['latest_processed']:
                            stats['latest_processed'] = row.get('latest_processed')
                
                stats['total_urls'] = total_count
                
                if total_completed + total_failed > 0:
                    stats['success_rate'] = (total_completed / (total_completed + total_failed)) * 100
                
                if total_count > 0:
                    stats['avg_attempts'] = total_attempts / total_count
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting domain processing stats: {e}")
            return {'error': str(e)}
    
    async def get_recent_failures(self, domain_id: Optional[int] = None, 
                                 limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent failed processing attempts"""
        try:
            where_conditions = ["status = 'failed'"]
            params = []
            
            if domain_id:
                where_conditions.append("domain_id = %s")
                params.append(domain_id)
            
            where_clause = " AND ".join(where_conditions)
            
            sql = f"""
            SELECT 
                original_url, domain_id, last_error, processing_attempts,
                processed_at, created_at
            FROM url_tracking 
            WHERE {where_clause}
            ORDER BY processed_at DESC
            LIMIT %s;
            """
            params.append(limit)
            
            results = self.db_manager.execute_sql(sql, tuple(params))
            
            failures = []
            if results:
                for row in results:
                    failure = {
                        'url': row.get('original_url'),
                        'domain_id': row.get('domain_id'),
                        'error': row.get('last_error'),
                        'attempts': row.get('processing_attempts'),
                        'failed_at': row.get('processed_at'),
                        'discovered_at': row.get('created_at')
                    }
                    failures.append(failure)
            
            return failures
            
        except Exception as e:
            logger.error(f"Error getting recent failures: {e}")
            return []
    
    async def get_processing_trends(self, domain_id: int, days_back: int = 30) -> Dict[str, Any]:
        """Get processing trends over time"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days_back)
            
            sql = """
            SELECT 
                DATE(processed_at) as processing_date,
                status,
                COUNT(*) as count
            FROM url_tracking 
            WHERE domain_id = %s AND processed_at >= %s
            GROUP BY DATE(processed_at), status
            ORDER BY processing_date DESC;
            """
            
            results = self.db_manager.execute_sql(sql, (domain_id, cutoff_date.isoformat()))
            
            trends = {
                'domain_id': domain_id,
                'period_days': days_back,
                'daily_stats': {},
                'totals': {
                    'completed': 0,
                    'failed': 0,
                    'discovered': 0
                }
            }
            
            if results:
                for row in results:
                    date = row.get('processing_date')
                    status = row.get('status')
                    count = int(row.get('count', 0))
                    
                    if date not in trends['daily_stats']:
                        trends['daily_stats'][date] = {
                            'completed': 0,
                            'failed': 0,
                            'discovered': 0,
                            'total': 0
                        }
                    
                    if status in trends['daily_stats'][date]:
                        trends['daily_stats'][date][status] = count
                        trends['daily_stats'][date]['total'] += count
                        
                        # Update totals
                        if status in trends['totals']:
                            trends['totals'][status] += count
            
            return trends
            
        except Exception as e:
            logger.error(f"Error getting processing trends: {e}")
            return {'error': str(e)}
    
    async def get_url_status(self, url: str) -> Optional[Dict[str, Any]]:
        """Get status information for specific URL"""
        try:
            sql = """
            SELECT 
                url_hash, original_url, normalized_url, domain_id,
                status, created_at, processed_at, expires_at,
                processing_attempts, last_error, metadata
            FROM url_tracking 
            WHERE original_url = %s OR normalized_url = %s;
            """
            
            results = self.db_manager.execute_sql(sql, (url, url))
            
            if results and len(results) > 0:
                row = results[0]
                return {
                    'url_hash': row.get('url_hash'),
                    'original_url': row.get('original_url'),
                    'normalized_url': row.get('normalized_url'),
                    'domain_id': row.get('domain_id'),
                    'status': row.get('status'),
                    'created_at': row.get('created_at'),
                    'processed_at': row.get('processed_at'),
                    'expires_at': row.get('expires_at'),
                    'processing_attempts': row.get('processing_attempts'),
                    'last_error': row.get('last_error'),
                    'metadata': row.get('metadata')
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting URL status: {e}")
            return None
    
    async def mark_urls_for_retry(self, urls: List[str], domain_id: int) -> int:
        """Mark failed URLs for retry"""
        try:
            if not urls:
                return 0
            
            # Reset failed URLs to discovered status
            url_placeholders = ','.join(['%s'] * len(urls))
            sql = f"""
            UPDATE url_tracking 
            SET status = 'discovered', last_error = NULL, 
                processing_attempts = 0, processed_at = NULL
            WHERE original_url IN ({url_placeholders}) 
            AND domain_id = %s AND status = 'failed';
            """
            
            params = urls + [domain_id]
            result = self.db_manager.execute_sql(sql, tuple(params))
            
            if result is not None:
                logger.info(f"Marked {len(urls)} URLs for retry in domain {domain_id}")
                return len(urls)
            
            return 0
            
        except Exception as e:
            logger.error(f"Error marking URLs for retry: {e}")
            return 0
    
    async def cleanup_expired_tracking(self) -> int:
        """Clean up expired URL tracking records"""
        try:
            sql = """
            DELETE FROM url_tracking 
            WHERE expires_at IS NOT NULL AND expires_at < NOW();
            """
            
            result = self.db_manager.execute_sql(sql)
            
            if result is not None:
                logger.info("Cleaned up expired URL tracking records")
                return 1
            
            return 0
            
        except Exception as e:
            logger.error(f"Error cleaning up expired tracking: {e}")
            return 0