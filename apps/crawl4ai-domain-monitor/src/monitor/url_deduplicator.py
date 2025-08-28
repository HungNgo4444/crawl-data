import logging
from typing import List, Tuple, Optional, Dict, Any
from datetime import datetime, timedelta

from ..models.url_models import URLEntry, URLStatus
from ..utils.url_utils import URLDeduplicator as URLFingerprintGenerator
from ..utils.database import DatabaseManager

logger = logging.getLogger(__name__)


class URLDeduplicator:
    """URL deduplication manager with database integration"""
    
    def __init__(self, db_manager: DatabaseManager, ttl_days: int = 30):
        self.db_manager = db_manager
        self.ttl_days = ttl_days
        self.fingerprint_generator = URLFingerprintGenerator()
        
    def is_duplicate(self, url: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Check if URL is already processed using fingerprint"""
        try:
            fingerprint = self.fingerprint_generator.generate_fingerprint(url)
            
            sql = """
            SELECT url_hash, original_url, normalized_url, domain_id, 
                   status, created_at, processed_at, expires_at
            FROM url_tracking 
            WHERE url_hash = %s AND (expires_at IS NULL OR expires_at > NOW());
            """
            
            results = self.db_manager.execute_sql(sql, (fingerprint,))
            
            if results and len(results) > 0:
                return True, results[0]
            else:
                return False, None
                
        except Exception as e:
            logger.error(f"Duplicate check error for '{url}': {e}")
            return False, None
    
    def mark_processed(self, url: str, domain_id: int, status: str, 
                      error: Optional[str] = None, metadata: Optional[Dict] = None) -> bool:
        """Mark URL as processed with status and timestamp"""
        try:
            fingerprint = self.fingerprint_generator.generate_fingerprint(url)
            normalized_url = self.fingerprint_generator.normalizer.normalize_url(url)
            expires_at = datetime.now() + timedelta(days=self.ttl_days)
            
            # Check if already exists
            is_dup, existing = self.is_duplicate(url)
            
            if is_dup:
                # Update existing record
                sql = """
                UPDATE url_tracking 
                SET status = %s, processed_at = NOW(), last_error = %s, 
                    processing_attempts = processing_attempts + 1,
                    metadata = %s
                WHERE url_hash = %s;
                """
                metadata_json = str(metadata or {}).replace("'", '"')
                result = self.db_manager.execute_sql(sql, (status, error, metadata_json, fingerprint))
            else:
                # Insert new record
                sql = """
                INSERT INTO url_tracking 
                (url_hash, original_url, normalized_url, domain_id, status, 
                 processed_at, expires_at, processing_attempts, last_error, metadata)
                VALUES (%s, %s, %s, %s, %s, NOW(), %s, 1, %s, %s);
                """
                metadata_json = str(metadata or {}).replace("'", '"')
                result = self.db_manager.execute_sql(sql, (
                    fingerprint, url, normalized_url, domain_id, status,
                    expires_at.isoformat(), error, metadata_json
                ))
            
            return result is not None
            
        except Exception as e:
            logger.error(f"Mark processed error for '{url}': {e}")
            return False
    
    def add_discovered_urls(self, urls: List[str], domain_id: int) -> Tuple[List[str], List[str]]:
        """Add discovered URLs, return (new_urls, duplicate_urls)"""
        try:
            new_urls = []
            duplicate_urls = []
            
            for url in urls:
                is_dup, _ = self.is_duplicate(url)
                if is_dup:
                    duplicate_urls.append(url)
                else:
                    # Add as discovered
                    fingerprint = self.fingerprint_generator.generate_fingerprint(url)
                    normalized_url = self.fingerprint_generator.normalizer.normalize_url(url)
                    expires_at = datetime.now() + timedelta(days=self.ttl_days)
                    
                    sql = """
                    INSERT INTO url_tracking 
                    (url_hash, original_url, normalized_url, domain_id, status, expires_at)
                    VALUES (%s, %s, %s, %s, 'discovered', %s)
                    ON CONFLICT (url_hash) DO NOTHING;
                    """
                    
                    result = self.db_manager.execute_sql(sql, (
                        fingerprint, url, normalized_url, domain_id, expires_at.isoformat()
                    ))
                    
                    if result is not None:
                        new_urls.append(url)
            
            return new_urls, duplicate_urls
            
        except Exception as e:
            logger.error(f"Add discovered URLs error: {e}")
            return [], urls  # Treat all as duplicates on error
    
    def cleanup_expired(self) -> int:
        """Remove expired URL tracking records"""
        try:
            sql = """
            DELETE FROM url_tracking 
            WHERE expires_at IS NOT NULL AND expires_at < NOW();
            """
            
            result = self.db_manager.execute_sql(sql)
            if result is not None:
                # Get count from psql output (simplified)
                return 1  # Return success indicator
            return 0
            
        except Exception as e:
            logger.error(f"Cleanup expired error: {e}")
            return 0
    
    def get_processing_queue(self, domain_id: int, limit: int = 100) -> List[Dict[str, Any]]:
        """Get URLs pending processing for domain"""
        try:
            sql = """
            SELECT url_hash, original_url, normalized_url, status, created_at
            FROM url_tracking 
            WHERE domain_id = %s AND status IN ('discovered', 'queued')
            ORDER BY created_at ASC
            LIMIT %s;
            """
            
            results = self.db_manager.execute_sql(sql, (domain_id, limit))
            return results or []
            
        except Exception as e:
            logger.error(f"Get processing queue error: {e}")
            return []
    
    def get_statistics(self, domain_id: Optional[int] = None) -> Dict[str, int]:
        """Get deduplication statistics"""
        try:
            where_clause = f"WHERE domain_id = {domain_id}" if domain_id else ""
            
            sql = f"""
            SELECT 
                status,
                COUNT(*) as count
            FROM url_tracking 
            {where_clause}
            GROUP BY status;
            """
            
            results = self.db_manager.execute_sql(sql)
            
            stats = {
                'discovered': 0,
                'queued': 0,  
                'processing': 0,
                'completed': 0,
                'failed': 0,
                'expired': 0
            }
            
            if results:
                for row in results:
                    status = row.get('status', '')
                    count = int(row.get('count', 0))
                    if status in stats:
                        stats[status] = count
            
            stats['total'] = sum(stats.values())
            return stats
            
        except Exception as e:
            logger.error(f"Get statistics error: {e}")
            return {'total': 0}